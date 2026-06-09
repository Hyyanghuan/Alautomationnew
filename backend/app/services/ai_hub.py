"""AI 智能中枢 - 多 Agent 协作"""
import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

settings = get_settings()


class AIModelError(Exception):
    """大模型 API 调用失败（余额、密钥、限流等）"""


def _format_api_error(provider: str, model: str, status: int, body: str) -> str:
    hints = {
        401: "API Key 无效或已过期",
        402: "账户余额不足，请充值或更换其他模型",
        403: "无权访问该模型",
        429: "请求过于频繁，请稍后重试",
        500: "模型服务暂时不可用",
        503: "模型服务繁忙",
    }
    hint = hints.get(status, f"HTTP {status}")
    detail = body[:200] if body else ""
    msg = f"[{provider}/{model}] 调用失败：{hint}"
    if detail and status not in hints:
        msg += f"（{detail}）"
    return msg


DESIGN_AGENT_PROMPT = """你是测试设计专家。根据以下功能/需求，生成测试点树（JSON嵌套结构）。
每个节点包含 id(字符串)、name、children(数组)。覆盖正常、异常、边界场景。
仅返回JSON，不要其他文字。

输入：
{input}
"""

CASE_GEN_PROMPT = """根据测试点生成结构化测试用例，JSON数组格式：
[{{"name":"","precondition":"","steps":[{{"action":"","input":""}}],"expected_result":"","priority":"P1|P2|P3","test_types":["功能"]}}]

测试点：{test_point}
仅返回JSON数组。
"""

HEALING_PROMPT = """分析测试失败日志，给出修复建议和修复后脚本片段。
失败日志：{log}
脚本：{script}
返回JSON: {{"root_cause":"","fixed_script":"","confidence":0.0-1.0}}
"""


class AIClient:
    """统一 AI 模型调用客户端"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.provider = provider or settings.ai_default_provider
        self.model = model or settings.ai_default_model
        self._api_key_override = api_key
        self._api_base_override = api_base

    def _get_config(self) -> tuple[str, str, str]:
        if self._api_key_override:
            if self._api_base_override:
                base = self._api_base_override
            elif self.provider == "deepseek":
                base = settings.deepseek_api_base
            elif self.provider == "qwen":
                base = settings.qwen_api_base
            else:
                base = settings.openai_api_base
            return base, self._api_key_override, self.model
        if self.provider == "openai":
            return settings.openai_api_base, settings.openai_api_key, self.model
        if self.provider == "qwen":
            return settings.qwen_api_base, settings.qwen_api_key, self.model
        if self.provider == "deepseek":
            return settings.deepseek_api_base, settings.deepseek_api_key, self.model
        return settings.openai_api_base, settings.openai_api_key, self.model

    async def chat(
        self,
        prompt: str,
        system: str = "你是专业测试AI助手。",
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        base_url, api_key, model = self._get_config()
        if not api_key:
            return self._mock_response(prompt)

        try:
            async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature if temperature is not None else settings.ai_default_temperature,
                        "top_p": top_p if top_p is not None else settings.ai_default_top_p,
                        "max_tokens": max_tokens if max_tokens is not None else settings.ai_default_max_tokens,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else ""
            raise AIModelError(
                _format_api_error(self.provider, model, e.response.status_code, body)
            ) from e
        except httpx.RequestError as e:
            raise AIModelError(f"[{self.provider}/{model}] 无法连接模型 API：{e}") from e

    def _mock_response(self, prompt: str) -> str:
        """无 API Key 时返回演示数据"""
        if "测试点" in prompt or "功能" in prompt:
            return json.dumps({
                "id": "TP-ROOT",
                "name": "功能测试",
                "children": [
                    {
                        "id": "TP-001",
                        "name": "正常流程",
                        "children": [{"id": "TP-001-01", "name": "基本场景", "children": []}],
                    },
                    {
                        "id": "TP-002",
                        "name": "异常流程",
                        "children": [{"id": "TP-002-01", "name": "错误处理", "children": []}],
                    },
                ],
            }, ensure_ascii=False)
        if "测试点：" in prompt:
            return json.dumps([{
                "name": "验证基本功能",
                "precondition": "系统已启动",
                "steps": [{"action": "执行操作", "input": "有效数据"}],
                "expected_result": "操作成功",
                "priority": "P1",
                "test_types": ["功能"],
            }], ensure_ascii=False)
        return json.dumps({"message": "请配置 .env 中的 AI API Key"})


class TestDesignAgent:
    async def generate_test_points(self, features_text: str, kb_context: str = "") -> dict:
        client = AIClient()
        prompt = DESIGN_AGENT_PROMPT.format(
            input=f"功能列表:\n{features_text}\n\n知识库参考:\n{kb_context or '无'}"
        )
        result = await client.chat(prompt)
        try:
            return json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError:
            return {"id": "TP-ROOT", "name": "解析失败", "children": []}

    async def generate_cases(self, test_point_name: str) -> List[dict]:
        client = AIClient()
        prompt = CASE_GEN_PROMPT.format(test_point=test_point_name)
        result = await client.chat(prompt)
        try:
            data = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return [{"name": f"{test_point_name}-用例", "priority": "P2", "test_types": ["功能"]}]


class HealingAgent:
    async def heal_script(self, log: str, script: str) -> Dict[str, Any]:
        client = AIClient()
        prompt = HEALING_PROMPT.format(log=log, script=script or "")
        result = await client.chat(prompt)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"root_cause": "解析失败", "fixed_script": script, "confidence": 0.0}


class IntentAgent:
    async def classify(self, user_input: str) -> str:
        mapping = {
            "测试点": "design",
            "用例": "design",
            "代码": "code_analysis",
            "修复": "healing",
            "缺陷": "defect_prediction",
        }
        for k, v in mapping.items():
            if k in user_input:
                return v
        return "design"


class AIHub:
    """多 Agent 编排入口"""

    def __init__(self):
        self.design = TestDesignAgent()
        self.healing = HealingAgent()
        self.intent = IntentAgent()

    async def orchestrate(self, user_input: str, context: dict) -> Dict[str, Any]:
        intent = await self.intent.classify(user_input)
        if intent == "design":
            tree = await self.design.generate_test_points(
                context.get("features_text", user_input),
                context.get("kb_context", ""),
            )
            return {"intent": intent, "result": tree}
        if intent == "healing":
            heal = await self.healing.heal_script(
                context.get("log", ""), context.get("script", "")
            )
            return {"intent": intent, "result": heal}
        return {"intent": intent, "message": "功能开发中"}
