"""执行器插件基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ExecutorResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ExecutorResult:
    status: ExecutorResultStatus
    log: str = ""
    duration_ms: int = 0
    screenshot_url: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class BaseExecutor(ABC):
    executor_type: str = "base"

    @abstractmethod
    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        pass
