"""执行器代码规则（完整源码，供执行中心查看）"""
from pathlib import Path

from app.executors.types import PLAN_EXECUTOR_OPTIONS, normalize_executor_type

_EXEC_DIR = Path(__file__).resolve().parent


def _read_source(*filenames: str) -> str:
    parts: list[str] = []
    for name in filenames:
        path = _EXEC_DIR / name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        parts.append(f"# ===== {name} =====\n{content}")
    return "\n\n".join(parts) if parts else ""


def _rules_for(executor_key: str) -> dict:
    base_rules = {
        "api": {
            "rules": [
                "计划创建时选择「接口/功能测试」，执行时绑定 APIExecutor",
                "用例 steps 为 JSON 数组，每项含 url、method、headers、body、expected_status",
                "支持 expected_body_contains、expected_json_path / expected_json_value 断言",
                "base_url 来自计划执行 environment 或默认 http://localhost:8000",
                "无 steps 时状态为 skipped",
            ],
            "case_format": {
                "steps": [
                    {
                        "url": "/api/v1/health",
                        "method": "GET",
                        "expected_status": 200,
                        "expected_body_contains": "ok",
                    }
                ]
            },
            "code_files": ["base.py", "api_executor.py"],
        },
        "unit": {
            "rules": [
                "计划选择「单元测试」，执行时绑定 UnitExecutor",
                "用例 script_content 存放完整 Pytest 可执行脚本",
                "在临时目录运行 pytest，超时默认 120s（environment.pytest_timeout）",
                "无 script_content 时 skipped",
            ],
            "case_format": {
                "script_content": "def test_demo():\n    assert 1 + 1 == 2"
            },
            "code_files": ["base.py", "unit_executor.py"],
        },
        "e2e": {
            "rules": [
                "计划选择「E2E / Web UI」，执行时绑定 E2EExecutor + Google Chrome",
                "首次执行自动下载 Chrome 到 PLAYWRIGHT_BROWSERS_PATH（默认 /app/data/browsers）",
                "截图保存至 PLAYWRIGHT_SCREENSHOTS_PATH（默认 /app/data/screenshots）",
                "steps 支持: goto、click、fill、assert_text、assert_visible、wait、screenshot",
                "定位策略: css（默认）、xpath、id、text、role",
                "environment: target_url、headless、screenshot、viewport",
            ],
            "case_format": {
                "steps": [
                    {"action": "goto", "url": "http://localhost:5173"},
                    {"action": "click", "strategy": "css", "selector": "#login-btn"},
                    {"action": "fill", "selector": "#username", "text": "admin"},
                    {"action": "assert_text", "selector": "h1", "text": "仪表盘"},
                ]
            },
            "code_files": ["base.py", "browser_manager.py", "e2e_executor.py"],
        },
        "performance": {
            "rules": [
                "计划选择「性能测试」，执行时绑定 PerformanceExecutor",
                "用例 performance 字段或 steps[0].url 指定压测目标",
                "支持 concurrency、total_requests、duration_sec、min_tps、max_avg_latency_ms",
                "返回 extra: tps、avg_latency_ms、p95_ms、errors、success",
            ],
            "case_format": {
                "performance": {
                    "url": "/api/v1/health",
                    "method": "GET",
                    "concurrency": 10,
                    "total_requests": 100,
                    "min_tps": 5,
                    "max_avg_latency_ms": 500,
                }
            },
            "code_files": ["base.py", "performance_executor.py"],
        },
        "agent": {
            "rules": [
                "计划选择「Agent 测试」，执行时绑定 AgentTestExecutor",
                "query 或 name 作为 Agent 输入，经 AIHub.orchestrate 编排",
                "可设 expected_intent、expected_contains 进行结果校验",
                "失败时记录完整 JSON 响应日志",
            ],
            "case_format": {
                "name": "验证登录意图识别",
                "query": "帮我生成登录功能的测试点",
                "expected_intent": "design",
            },
            "code_files": ["base.py", "agent_test_executor.py"],
        },
    }
    meta = base_rules[executor_key]
    opt = next((o for o in PLAN_EXECUTOR_OPTIONS if o["value"] == executor_key), {})
    code_sample = _read_source(*meta["code_files"])
    return {
        "type": executor_key,
        "name": opt.get("name", executor_key),
        "tech": opt.get("tech", ""),
        "description": opt.get("description", ""),
        "rules": meta["rules"],
        "case_format": meta["case_format"],
        "code_sample": code_sample,
        "code_files": meta["code_files"],
    }


EXECUTOR_RULES: dict[str, dict] = {k: _rules_for(k) for k in ("api", "unit", "e2e", "performance", "agent")}


def get_executor_rule(executor_type: str) -> dict | None:
    key = normalize_executor_type(executor_type)
    return EXECUTOR_RULES.get(key)


def list_all_rules() -> list[dict]:
    return [
        {
            "type": v["type"],
            "name": v["name"],
            "tech": v["tech"],
            "description": v["description"],
        }
        for v in EXECUTOR_RULES.values()
    ]
