import time
from typing import Any
from urllib.parse import urljoin

import httpx

from app.executors.base import BaseExecutor, ExecutorResult, ExecutorResultStatus


class APIExecutor(BaseExecutor):
    executor_type = "api"

    def _resolve_url(self, step: dict, base_url: str) -> str:
        url = step.get("url") or "/health"
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))

    async def _run_step(self, client: httpx.AsyncClient, step: dict, base_url: str) -> tuple[bool, str]:
        url = self._resolve_url(step, base_url)
        method = (step.get("method") or "GET").upper()
        headers = step.get("headers") or {}
        body = step.get("body")
        params = step.get("params")
        timeout = step.get("timeout", 30)
        expected_status = step.get("expected_status", 200)
        expected_body_contains = step.get("expected_body_contains")

        kwargs: dict[str, Any] = {"headers": headers, "timeout": timeout}
        if params:
            kwargs["params"] = params
        if body is not None and method in ("POST", "PUT", "PATCH", "DELETE"):
            kwargs["json"] = body

        resp = await client.request(method, url, **kwargs)
        line = f"{method} {url} -> {resp.status_code}"
        if resp.status_code != expected_status:
            preview = (resp.text or "")[:300]
            return False, f"{line}\n期望状态码 {expected_status}，实际 {resp.status_code}\n响应: {preview}"

        if expected_body_contains:
            text = resp.text or ""
            if expected_body_contains not in text:
                return False, f"{line}\n响应体未包含: {expected_body_contains}"

        json_path = step.get("expected_json_path")
        json_value = step.get("expected_json_value")
        if json_path and json_value is not None:
            try:
                data = resp.json()
            except Exception:
                return False, f"{line}\n响应非 JSON，无法断言路径 {json_path}"
            parts = json_path.split(".")
            cur: Any = data
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    cur = None
                    break
            if cur != json_value:
                return False, f"{line}\nJSON 路径 {json_path} 期望 {json_value}，实际 {cur}"

        return True, line

    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        start = time.time()
        steps = case_data.get("steps") or []
        base_url = env_config.get("base_url", "http://localhost:8000")
        log_lines: list[str] = []

        if not steps:
            return ExecutorResult(
                status=ExecutorResultStatus.SKIPPED,
                log="无 steps 步骤，接口用例跳过",
                duration_ms=int((time.time() - start) * 1000),
            )

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                for i, step in enumerate(steps, 1):
                    ok, msg = await self._run_step(client, step, base_url)
                    log_lines.append(f"[步骤{i}] {msg}")
                    if not ok:
                        return ExecutorResult(
                            status=ExecutorResultStatus.FAILED,
                            log="\n".join(log_lines),
                            duration_ms=int((time.time() - start) * 1000),
                        )
            return ExecutorResult(
                status=ExecutorResultStatus.PASSED,
                log="\n".join(log_lines),
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            log_lines.append(f"异常: {e}")
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log="\n".join(log_lines),
                duration_ms=int((time.time() - start) * 1000),
            )
