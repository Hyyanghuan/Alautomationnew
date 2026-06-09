"""计划级执行器类型定义"""

PLAN_EXECUTOR_OPTIONS: list[dict] = [
    {
        "value": "api",
        "label": "接口/功能测试",
        "name": "接口测试",
        "tech": "httpx + 步骤驱动",
        "description": "基于 HTTP 请求步骤串联，断言状态码与响应。",
    },
    {
        "value": "unit",
        "label": "单元测试",
        "name": "单元测试",
        "tech": "Pytest",
        "description": "执行用例 script_content 中的 Pytest 脚本。",
    },
    {
        "value": "e2e",
        "label": "E2E / Web UI",
        "name": "E2E/UI测试",
        "tech": "Playwright + Google Chrome",
        "description": "使用 Chrome 浏览器进行页面自动化，支持步骤驱动与截图。",
    },
    {
        "value": "performance",
        "label": "性能测试",
        "name": "性能测试",
        "tech": "asyncio 并发压测",
        "description": "并发 HTTP 压测，采集 TPS 与平均延迟。",
    },
    {
        "value": "agent",
        "label": "Agent 测试",
        "name": "Agent测试",
        "tech": "AIHub 编排",
        "description": "调用 AI 智能中枢验证 Agent 意图与输出。",
    },
]

# 用例测试类型名 -> 计划执行器（兜底映射，计划未指定时使用）
CASE_TYPE_TO_EXECUTOR: dict[str, str] = {
    "功能": "api",
    "接口": "api",
    "api": "api",
    "integration": "api",
    "unit": "unit",
    "e2e": "e2e",
    "uat": "e2e",
    "ui": "e2e",
    "web页面": "e2e",
    "性能": "performance",
    "performance": "performance",
    "agent": "agent",
    "agent测试": "agent",
}


def normalize_executor_type(value: str | None, fallback: str = "api") -> str:
    if not value:
        return fallback
    key = value.strip().lower()
    if key in {o["value"] for o in PLAN_EXECUTOR_OPTIONS}:
        return key
    return CASE_TYPE_TO_EXECUTOR.get(key, CASE_TYPE_TO_EXECUTOR.get(value, fallback))
