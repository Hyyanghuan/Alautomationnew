"""执行器插件注册表"""
from typing import Dict, Type

from app.executors.base import BaseExecutor
from app.executors.api_executor import APIExecutor
from app.executors.unit_executor import UnitExecutor
from app.executors.e2e_executor import E2EExecutor
from app.executors.performance_executor import PerformanceExecutor
from app.executors.agent_test_executor import AgentTestExecutor
from app.executors.types import PLAN_EXECUTOR_OPTIONS, normalize_executor_type

_REGISTRY: Dict[str, Type[BaseExecutor]] = {
    "unit": UnitExecutor,
    "api": APIExecutor,
    "integration": APIExecutor,
    "e2e": E2EExecutor,
    "uat": E2EExecutor,
    "performance": PerformanceExecutor,
    "ui": E2EExecutor,
    "agent": AgentTestExecutor,
    "功能": APIExecutor,
    "接口": APIExecutor,
    "性能": PerformanceExecutor,
    "web页面": E2EExecutor,
    "agent测试": AgentTestExecutor,
}


def get_executor(test_type: str) -> BaseExecutor:
    key = normalize_executor_type(test_type)
    cls = _REGISTRY.get(key) or _REGISTRY.get(test_type.lower(), APIExecutor)
    return cls()


def list_executors() -> list[dict]:
    return [
        {
            "type": o["value"],
            "name": o["name"],
            "tech": o["tech"],
            "description": o["description"],
            "label": o["label"],
        }
        for o in PLAN_EXECUTOR_OPTIONS
    ]
