"""Telegram 测试报告推送"""
import json
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.test_plan import TestExecution, TestExecutionResult

settings = get_settings()

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "telegram_config.json"


def _mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "****"
    return f"{'*' * (len(token) - 6)}{token[-6:]}"


def _load_file_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_file_config(data: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_telegram_config() -> dict:
    """合并 .env 默认值与运行时 JSON 配置"""
    file_cfg = _load_file_config()
    token = file_cfg.get("bot_token") or settings.telegram_bot_token
    chat_id = file_cfg.get("chat_id") if "chat_id" in file_cfg else settings.telegram_chat_id
    enabled = file_cfg.get("enabled") if "enabled" in file_cfg else settings.telegram_enabled
    auto_send = (
        file_cfg.get("auto_send_after_execution")
        if "auto_send_after_execution" in file_cfg
        else settings.telegram_auto_send
    )
    return {
        "enabled": bool(enabled),
        "chat_id": str(chat_id or ""),
        "bot_token": str(token or ""),
        "auto_send_after_execution": bool(auto_send),
    }


def get_telegram_config_public() -> dict:
    cfg = get_telegram_config()
    token = cfg.get("bot_token", "")
    return {
        "enabled": cfg["enabled"],
        "chat_id": cfg["chat_id"],
        "bot_token_set": bool(token),
        "bot_token_masked": _mask_token(token),
        "auto_send_after_execution": cfg["auto_send_after_execution"],
    }


def update_telegram_config(
    *,
    enabled: Optional[bool] = None,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    auto_send_after_execution: Optional[bool] = None,
) -> dict:
    file_cfg = _load_file_config()
    current = get_telegram_config()

    if enabled is not None:
        file_cfg["enabled"] = enabled
    if chat_id is not None:
        file_cfg["chat_id"] = chat_id.strip()
    if bot_token is not None and bot_token.strip():
        file_cfg["bot_token"] = bot_token.strip()
    if auto_send_after_execution is not None:
        file_cfg["auto_send_after_execution"] = auto_send_after_execution

    _save_file_config(file_cfg)
    return get_telegram_config_public()


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_report_message(ex: TestExecution, results: list[TestExecutionResult]) -> str:
    status_map = {
        "passed": "✅ 通过",
        "failed": "❌ 失败",
        "running": "⏳ 执行中",
        "pending": "⏳ 待执行",
        "skipped": "⏭ 跳过",
        "error": "⚠️ 异常",
    }
    status_text = status_map.get(ex.status.value, ex.status.value)
    pass_rate = round(ex.passed_cases / ex.total_cases * 100, 1) if ex.total_cases else 0
    started = ex.started_at.strftime("%Y-%m-%d %H:%M:%S") if ex.started_at else "-"
    finished = ex.finished_at.strftime("%Y-%m-%d %H:%M:%S") if ex.finished_at else "-"

    lines = [
        "<b>📋 AI 自动化测试报告</b>",
        "",
        f"<b>计划：</b>{_escape_html(ex.plan_name or '-')}",
        f"<b>状态：</b>{status_text}",
        f"<b>执行人：</b>{_escape_html(ex.executor_name or '-')}",
        f"<b>通过率：</b>{pass_rate}% ({ex.passed_cases}/{ex.total_cases})",
        f"<b>失败：</b>{ex.failed_cases}  <b>跳过：</b>{ex.skipped_cases}",
        f"<b>耗时：</b>{ex.duration_ms or 0} ms",
        f"<b>开始：</b>{started}",
        f"<b>结束：</b>{finished}",
    ]
    if ex.summary:
        lines.extend(["", f"<b>摘要：</b>{_escape_html(ex.summary)}"])

    failed = [r for r in results if r.status.value == "failed"]
    if failed:
        lines.extend(["", "<b>失败用例：</b>"])
        for r in failed[:10]:
            lines.append(f"• {_escape_html(r.case_name or str(r.case_id))}")
        if len(failed) > 10:
            lines.append(f"… 另有 {len(failed) - 10} 条")

    return "\n".join(lines)


async def send_telegram_message(text: str, *, bot_token: str, chat_id: str) -> dict:
    if not bot_token or not chat_id:
        raise ValueError("Telegram Bot Token 或群组 ID 未配置")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
    data = resp.json()
    if resp.status_code != 200 or not data.get("ok"):
        desc = data.get("description") or resp.text
        raise RuntimeError(f"Telegram 发送失败: {desc}")
    return data


async def send_test_message() -> str:
    cfg = get_telegram_config()
    if not cfg["enabled"]:
        raise ValueError("Telegram 推送未启用")
    await send_telegram_message(
        "<b>🔔 测试消息</b>\n\nAI 自动化测试平台 Telegram 配置正常。",
        bot_token=cfg["bot_token"],
        chat_id=cfg["chat_id"],
    )
    return "测试消息已发送到 Telegram 群组"


async def send_execution_report(db: AsyncSession, execution_id: UUID) -> str:
    cfg = get_telegram_config()
    if not cfg["enabled"]:
        raise ValueError("Telegram 推送未启用，请先在报告页配置并启用")

    ex = await db.get(TestExecution, execution_id)
    if not ex:
        raise ValueError("执行记录不存在")

    results = (
        await db.execute(
            select(TestExecutionResult)
            .where(TestExecutionResult.execution_id == execution_id)
            .order_by(TestExecutionResult.created_at)
        )
    ).scalars().all()

    message = format_report_message(ex, list(results))
    await send_telegram_message(
        message,
        bot_token=cfg["bot_token"],
        chat_id=cfg["chat_id"],
    )
    return "测试报告已发送到 Telegram 群组"


async def try_auto_send_report(db: AsyncSession, execution_id: UUID) -> None:
    """执行完成后自动推送，失败不影响主流程"""
    cfg = get_telegram_config()
    if not cfg["enabled"] or not cfg["auto_send_after_execution"]:
        return
    try:
        await send_execution_report(db, execution_id)
    except Exception:
        pass
