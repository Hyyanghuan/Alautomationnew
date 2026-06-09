"""Agent 智能体执行器 - 绑定 AI 模型并执行提示词"""
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentInstance, AgentStatus, AgentType
from app.models.ai_model import AIModelConfig
from app.services.ai_hub import AIClient

DEFAULT_PROMPTS = {
    AgentType.HEALING: {
        "heal": """你是自愈修复智能体。分析失败日志与原始脚本，返回 JSON：
{{"root_cause":"","fixed_script":"","confidence":0.0-1.0}}

日志：
{log}

脚本：
{script}
仅返回 JSON。""",
    },
    AgentType.DESIGN: {
        "test_points": """你是测试设计智能体。根据需求文档与功能列表，生成测试点树（JSON嵌套）。
每个节点: id(字符串)、name、children(数组)。覆盖正常/异常/边界场景。仅返回JSON。

{input}""",
        "test_cases": """你是测试设计智能体。根据测试点生成结构化用例，JSON数组：
[{{"name":"","precondition":"","steps":[{{"action":"","input":""}}],"expected_result":"","priority":"P1|P2|P3","test_types":["功能"]}}]

测试点：{test_point}
需求参考：{requirements}
仅返回JSON数组。""",
        "verify_cases": """你是测试用例核查智能体。审查以下用例的完整性、可执行性、预期结果合理性。
返回JSON: {{"score":0-100,"issues":[{{"case_name":"","problem":"","suggestion":""}}],"summary":""}}

用例列表：
{cases}""",
    },
}


def _strip_markdown_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _try_repair_json(text: str) -> Any | None:
    start = text.find("{")
    if start < 0:
        start = text.find("[")
    if start < 0:
        return None
    fragment = text[start:]
    for end in range(len(fragment), max(1, len(fragment) - 2000), -1):
        try:
            return json.loads(fragment[:end])
        except json.JSONDecodeError:
            continue
    open_braces = fragment.count("{") - fragment.count("}")
    open_brackets = fragment.count("[") - fragment.count("]")
    suffix = "]" * max(0, open_brackets) + "}" * max(0, open_braces)
    if suffix:
        try:
            return json.loads(fragment + suffix)
        except json.JSONDecodeError:
            pass
    return None


def _parse_json(text: str, fallback: Any, *, strict: bool = False) -> Any:
    cleaned = _strip_markdown_json(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = _try_repair_json(cleaned)
        if repaired is not None:
            return repaired
        if strict:
            preview = cleaned[:200].replace("\n", " ")
            raise ValueError(
                f"AI 返回内容无法解析为 JSON（可能需求过长导致输出被截断）。片段：{preview}..."
            )
        return fallback


class AgentRunner:
    def __init__(self, db: AsyncSession, agent_id: UUID):
        self.db = db
        self.agent_id = agent_id
        self._agent: Optional[AgentInstance] = None
        self._client: Optional[AIClient] = None

    async def load(self) -> AgentInstance:
        agent = await self.db.get(AgentInstance, self.agent_id)
        if not agent:
            raise ValueError("Agent 不存在")
        if agent.status != AgentStatus.ENABLED:
            raise ValueError("Agent 已禁用")
        self._agent = agent
        provider, model, api_key, api_base = None, None, None, None
        if agent.model_id:
            model_cfg = await self.db.get(AIModelConfig, agent.model_id)
            if model_cfg and model_cfg.is_enabled:
                provider = model_cfg.provider
                model = model_cfg.model_name
                api_key = model_cfg.api_key_encrypted
                api_base = model_cfg.api_endpoint
        self._client = AIClient(
            provider=provider,
            model=model,
            api_key=api_key,
            api_base=api_base,
        )
        return agent

    def _agent_files(self) -> dict:
        if not self._agent or not self._agent.config:
            return {}
        return self._agent.config.get("agent_files", {})

    def _system_prompt(self) -> str:
        files = self._agent_files()
        prompts = files.get("prompts", {})
        return prompts.get("system-prompt.md") or "你是企业级测试智能体。"

    def _prompt(self, task: str, **kwargs) -> str:
        agent = self._agent
        files = self._agent_files()
        prompts = files.get("prompts", {})
        task_prompts = prompts.get("task-prompts.json") or {}
        template = task_prompts.get(task) if isinstance(task_prompts, dict) else None
        if not template and agent and agent.prompt_template and task in ("test_points", "test_cases", "verify_cases"):
            template = agent.prompt_template if task == "test_points" else None
        if not template:
            defaults = DEFAULT_PROMPTS.get(agent.agent_type, {}) if agent else {}
            template = defaults.get(task, prompts.get("task-router.md") or "请处理：\n{input}")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template.replace("{input}", kwargs.get("input", ""))

    def _read_model_params(self, task: str) -> tuple[float | None, float | None, int | None]:
        params = (self._agent.config or {}).get("agent_files", {}).get("configs", {})
        yaml_text = params.get("model-settings.yaml", "")
        temp, top_p, max_tokens = None, None, None
        for line in yaml_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if k == "temperature":
                    temp = float(v)
                elif k == "top_p":
                    top_p = float(v)
                elif k == "max_tokens":
                    max_tokens = int(v)
        if task in ("test_points", "test_cases") and (max_tokens is None or max_tokens < 8192):
            max_tokens = 8192
        return temp, top_p, max_tokens

    async def run(self, task: str, system: str | None = None, **kwargs) -> str:
        if not self._client:
            await self.load()
        prompt = self._prompt(task, **kwargs)
        sys_prompt = system or self._system_prompt()
        temp, top_p, max_tokens = self._read_model_params(task)
        return await self._client.chat(prompt, system=sys_prompt, temperature=temp, top_p=top_p, max_tokens=max_tokens)

    _TEST_POINT_TYPE_HINTS = {
        "功能": "生成功能测试点，关注业务流程、输入输出、权限与异常场景。",
        "接口": "生成 API 接口测试点，关注请求参数、响应码、鉴权、边界与错误处理。节点名应体现接口路径或方法。",
        "Web页面": (
            "生成 Web UI 页面测试点。每个可交互叶子节点必须包含 locator 对象："
            '{"strategy":"css|xpath|id|text|role","value":"选择器","description":"元素说明"}。'
            "例如登录按钮: {\"strategy\":\"css\",\"value\":\"#login-btn\",\"description\":\"登录按钮\"}"
        ),
        "Agent测试": "生成 Agent 自动化测试点，关注智能体对话流程、意图识别、回复准确性与异常兜底。",
    }

    async def generate_test_points(
        self,
        requirements: str,
        features_text: str = "",
        kb_context: str = "",
        test_point_type: str = "功能",
        web_page_url: str = "",
        web_locator_hint: str = "",
    ) -> dict:
        type_hint = self._TEST_POINT_TYPE_HINTS.get(test_point_type, self._TEST_POINT_TYPE_HINTS["功能"])
        web_extra = ""
        if test_point_type == "Web页面":
            if web_page_url:
                web_extra += f"\n- 目标页面 URL：{web_page_url}"
            if web_locator_hint:
                web_extra += f"\n- 元素定位参考：{web_locator_hint}"
        input_text = (
            f"## 测试点类型\n{test_point_type}\n{type_hint}{web_extra}\n\n"
            f"## 需求文档\n{requirements}\n\n"
            f"## 功能列表\n{features_text or '无'}\n\n"
            f"## 知识库参考\n{kb_context or '无'}\n\n"
            "每个节点 JSON 格式: "
            '{"id":"字符串","name":"名称","test_type":"'
            f'{test_point_type}'
            '","locator":{可选,Web页面叶子节点必填},"children":[]}'
        )
        result = await self.run("test_points", input=input_text)
        return _parse_json(result, {"id": "TP-ROOT", "name": "生成失败", "children": []}, strict=True)

    async def generate_cases(
        self, test_point_name: str, requirements: str = "", kb_context: str = ""
    ) -> List[dict]:
        req = requirements[:8000] if requirements else "无"
        if kb_context:
            req = f"{req}\n\n## 知识库参考\n{kb_context[:4000]}"
        result = await self.run(
            "test_cases",
            test_point=test_point_name,
            requirements=req,
        )
        data = _parse_json(result, [], strict=True)
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []

    async def verify_cases(self, cases_payload: List[dict]) -> dict:
        cases_str = json.dumps(cases_payload, ensure_ascii=False, indent=2)
        result = await self.run("verify_cases", cases=cases_str)
        return _parse_json(
            result,
            {"score": 0, "issues": [], "summary": "核查解析失败"},
        )

    async def heal_script(self, log: str, script: str) -> dict:
        result = await self.run("heal", log=log, script=script)
        return _parse_json(
            result,
            {"root_cause": "解析失败", "fixed_script": None, "confidence": 0},
        )


async def get_agent_or_default(
    db: AsyncSession,
    agent_id: Optional[UUID],
    agent_type: AgentType = AgentType.DESIGN,
    project_id: Optional[UUID] = None,
) -> UUID:
    if agent_id:
        agent = await db.get(AgentInstance, agent_id)
        if not agent:
            raise ValueError("指定的 Agent 不存在")
        if agent.status != AgentStatus.ENABLED:
            raise ValueError("指定的 Agent 已禁用")
        if agent.agent_type != agent_type:
            raise ValueError(f"Agent 类型不匹配，需要 {agent_type.value}")
        return agent_id

    if project_id:
        q = await db.execute(
            select(AgentInstance).where(
                AgentInstance.agent_type == agent_type,
                AgentInstance.status == AgentStatus.ENABLED,
                AgentInstance.project_id == project_id,
            ).limit(1)
        )
        agent = q.scalar_one_or_none()
        if agent:
            return agent.id

    q = await db.execute(
        select(AgentInstance).where(
            AgentInstance.agent_type == agent_type,
            AgentInstance.status == AgentStatus.ENABLED,
            AgentInstance.project_id.is_(None),
        ).limit(1)
    )
    agent = q.scalar_one_or_none()
    if agent:
        return agent.id

    q2 = await db.execute(
        select(AgentInstance).where(
            AgentInstance.agent_type == agent_type,
            AgentInstance.status == AgentStatus.ENABLED,
        ).limit(1)
    )
    agent2 = q2.scalar_one_or_none()
    if not agent2:
        type_labels = {
            AgentType.DESIGN: "测试设计",
            AgentType.HEALING: "自愈修复",
            AgentType.CODE_ANALYSIS: "代码分析",
            AgentType.DEFECT_PREDICTION: "缺陷预测",
        }
        label = type_labels.get(agent_type, agent_type.value)
        raise ValueError(f"未找到可用的{label} Agent，请先在 Agent 管理中创建并绑定模型")
    return agent2.id
