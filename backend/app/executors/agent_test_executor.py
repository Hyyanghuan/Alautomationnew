import json
import time

from app.executors.base import BaseExecutor, ExecutorResult, ExecutorResultStatus
from app.services.ai_hub import AIHub


class AgentTestExecutor(BaseExecutor):
    executor_type = "agent"

    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        start = time.time()
        query = (
            case_data.get("query")
            or case_data.get("name")
            or (case_data.get("steps") and str(case_data["steps"]))
            or ""
        ).strip()
        if not query:
            return ExecutorResult(
                status=ExecutorResultStatus.SKIPPED,
                log="无 query/name 输入，Agent 测试跳过",
                duration_ms=int((time.time() - start) * 1000),
            )

        context = {
            "features_text": env_config.get("features_text", query),
            "kb_context": env_config.get("kb_context", ""),
            "log": case_data.get("log", ""),
            "script": case_data.get("script_content", ""),
            "expected_intent": case_data.get("expected_intent") or env_config.get("expected_intent"),
            "expected_contains": case_data.get("expected_contains") or env_config.get("expected_contains"),
        }

        try:
            hub = AIHub()
            result = await hub.orchestrate(query, context)
            log_obj = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)

            passed = True
            reasons: list[str] = []

            if "error" in (result or {}):
                passed = False
                reasons.append("返回含 error")

            expected_intent = context.get("expected_intent")
            if expected_intent and result.get("intent") != expected_intent:
                passed = False
                reasons.append(f"意图不匹配: 期望 {expected_intent}, 实际 {result.get('intent')}")

            expected_contains = context.get("expected_contains")
            if expected_contains and expected_contains not in log_obj:
                passed = False
                reasons.append(f"输出未包含: {expected_contains}")

            if passed and "result" not in result and "message" in result:
                if "开发中" in str(result.get("message", "")):
                    passed = False
                    reasons.append("Agent 功能未就绪")

            status = ExecutorResultStatus.PASSED if passed else ExecutorResultStatus.FAILED
            log = log_obj
            if reasons:
                log = "失败原因: " + "; ".join(reasons) + "\n\n" + log_obj

            return ExecutorResult(
                status=status,
                log=log,
                duration_ms=int((time.time() - start) * 1000),
                extra={"intent": result.get("intent") if isinstance(result, dict) else None},
            )
        except Exception as e:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )
