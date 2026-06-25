"""API 请求校验工具与常量"""
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationInfo

from app.executors.executor_rules import get_executor_rule
from app.executors.types import PLAN_EXECUTOR_OPTIONS, normalize_executor_type

VALID_EXECUTOR_TYPES = frozenset(o["value"] for o in PLAN_EXECUTOR_OPTIONS)
VALID_TEST_POINT_TYPES = frozenset({"功能", "接口", "Web页面", "Agent测试"})
VALID_LOCATOR_STRATEGIES = frozenset({"css", "xpath", "id", "text", "role"})


def strip_required_str(value: str, *, field_name: str = "字段", min_len: int = 1, max_len: int = 500) -> str:
    text = (value or "").strip()
    if len(text) < min_len:
        raise ValueError(f"{field_name}不能为空")
    if len(text) > max_len:
        raise ValueError(f"{field_name}长度不能超过 {max_len} 个字符")
    return text


def strip_optional_str(value: str | None, *, max_len: int = 2000) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"长度不能超过 {max_len} 个字符")
    return text


def validate_executor_type_field(value: str) -> str:
    normalized = normalize_executor_type(value, "")
    if normalized not in VALID_EXECUTOR_TYPES or not get_executor_rule(normalized):
        allowed = ", ".join(sorted(VALID_EXECUTOR_TYPES))
        raise ValueError(f"执行器类型无效，允许值: {allowed}")
    return normalized


def validate_test_point_type_field(value: str) -> str:
    text = (value or "").strip()
    if text not in VALID_TEST_POINT_TYPES:
        allowed = ", ".join(sorted(VALID_TEST_POINT_TYPES))
        raise ValueError(f"测试点类型无效，允许值: {allowed}")
    return text


def validate_optional_url(value: str | None, *, field_name: str = "URL") -> str | None:
    text = strip_optional_str(value, max_len=2000)
    if text is None:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{field_name} 须以 http:// 或 https:// 开头")
    if not parsed.netloc:
        raise ValueError(f"{field_name} 格式无效")
    return text


def validate_uuid_list(value: list[Any], *, field_name: str = "ID列表", min_items: int = 1, max_items: int = 500) -> list:
    if len(value) < min_items:
        raise ValueError(f"{field_name}至少包含 {min_items} 项")
    if len(value) > max_items:
        raise ValueError(f"{field_name}不能超过 {max_items} 项")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name}存在重复项")
    return value


def validate_execution_environment(env: dict | None) -> dict | None:
    if env is None:
        return None
    if not isinstance(env, dict):
        raise ValueError("environment 必须是 JSON 对象")
    allowed_keys = {
        "base_url", "target_url", "headless", "screenshot", "docker",
        "viewport", "concurrency", "total_requests", "pytest_timeout", "env",
    }
    unknown = set(env.keys()) - allowed_keys
    if unknown:
        raise ValueError(f"environment 含未知字段: {', '.join(sorted(unknown))}")
    result = dict(env)
    if "base_url" in result and result["base_url"]:
        result["base_url"] = validate_optional_url(str(result["base_url"]), field_name="base_url")
    if "target_url" in result and result["target_url"]:
        result["target_url"] = validate_optional_url(str(result["target_url"]), field_name="target_url")
    return result


def validate_steps_field(value: list | None, info: ValidationInfo) -> list | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("steps 必须是数组")
    if len(value) > 200:
        raise ValueError("steps 步骤数不能超过 200")
    for i, step in enumerate(value, 1):
        if isinstance(step, str):
            if not step.strip():
                raise ValueError(f"steps 第 {i} 步不能为空")
            continue
        if isinstance(step, dict):
            if not step:
                raise ValueError(f"steps 第 {i} 步不能为空对象")
            continue
        raise ValueError(f"steps 第 {i} 步格式无效，须为字符串或对象")
    return value
