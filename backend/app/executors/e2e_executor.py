import re
import time
import uuid
from typing import Any
from urllib.parse import urljoin

from app.executors.base import BaseExecutor, ExecutorResult, ExecutorResultStatus
from app.executors.browser_manager import ensure_chrome_ready, get_browsers_path, get_screenshots_path


class E2EExecutor(BaseExecutor):
    executor_type = "e2e"

    def _locator(self, page, step: dict):
        strategy = (step.get("strategy") or step.get("locator_strategy") or "css").lower()
        value = step.get("selector") or step.get("value") or step.get("locator_value") or ""
        if not value:
            raise ValueError("步骤缺少 selector/value 定位值")
        if strategy == "xpath":
            return page.locator(f"xpath={value}")
        if strategy == "text":
            return page.get_by_text(value)
        if strategy == "role":
            role = step.get("role", "button")
            return page.get_by_role(role, name=value)
        if strategy == "id":
            return page.locator(f"#{value.lstrip('#')}")
        return page.locator(value)

    async def _run_step(self, page, step: dict, base_url: str, log_lines: list[str]) -> None:
        action = (step.get("action") or "goto").lower()
        if action == "goto":
            url = step.get("url") or base_url
            if url and not url.startswith("http"):
                url = urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))
            await page.goto(url, wait_until=step.get("wait_until", "domcontentloaded"))
            log_lines.append(f"goto {url}")
            return

        if action == "click":
            loc = self._locator(page, step)
            await loc.click(timeout=step.get("timeout", 10000))
            log_lines.append(f"click {step.get('selector') or step.get('value')}")
            return

        if action == "fill":
            loc = self._locator(page, step)
            await loc.fill(step.get("text") or step.get("value_input") or "", timeout=step.get("timeout", 10000))
            log_lines.append(f"fill {step.get('selector') or step.get('value')}")
            return

        if action == "assert_text":
            loc = self._locator(page, step)
            expected = step.get("text") or step.get("expected") or ""
            actual = await loc.inner_text()
            if expected not in actual:
                raise AssertionError(f"文本断言失败: 期望包含 '{expected}'，实际 '{actual}'")
            log_lines.append(f"assert_text ok: {expected}")
            return

        if action == "assert_visible":
            loc = self._locator(page, step)
            if not await loc.is_visible():
                raise AssertionError(f"元素不可见: {step.get('selector') or step.get('value')}")
            log_lines.append(f"assert_visible ok")
            return

        if action == "wait":
            ms = int(step.get("ms") or step.get("timeout") or 1000)
            await page.wait_for_timeout(ms)
            log_lines.append(f"wait {ms}ms")
            return

        if action == "screenshot":
            name = re.sub(r"[^\w\-]", "_", step.get("name", "shot"))
            path = get_screenshots_path() / f"{name}_{uuid.uuid4().hex[:8]}.png"
            await page.screenshot(path=str(path), full_page=step.get("full_page", True))
            log_lines.append(f"screenshot {path}")
            return

        raise ValueError(f"不支持的 E2E 动作: {action}")

    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        start = time.time()
        log_lines: list[str] = []
        screenshot_url: str | None = None

        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=f"未安装 playwright: {e}",
                duration_ms=int((time.time() - start) * 1000),
            )

        try:
            browsers_path = ensure_chrome_ready()
            log_lines.append(f"Chrome 路径: {browsers_path}")
        except Exception as e:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=f"Chrome 准备失败: {e}",
                duration_ms=int((time.time() - start) * 1000),
            )

        base_url = env_config.get("target_url") or env_config.get("base_url") or "about:blank"
        headless = env_config.get("headless", True)
        steps: list[dict] = case_data.get("steps") or []
        script = (case_data.get("script_content") or "").strip()

        if not steps and not script and base_url == "about:blank":
            return ExecutorResult(
                status=ExecutorResultStatus.SKIPPED,
                log="无 steps/script_content 且未配置 target_url",
                duration_ms=int((time.time() - start) * 1000),
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"] if env_config.get("docker") else [],
                )
                context = await browser.new_context(
                    viewport=env_config.get("viewport") or {"width": 1280, "height": 720},
                )
                page = await context.new_page()

                if steps:
                    for step in steps:
                        await self._run_step(page, step, base_url, log_lines)
                elif script:
                    log_lines.append("执行 script_content（简化模式：仅支持 page.goto 单行）")
                    matched = False
                    if "page.goto" in script:
                        m = re.search(r'page\.goto\(["\']([^"\']+)["\']\)', script)
                        if m:
                            await page.goto(m.group(1))
                            log_lines.append(f"goto {m.group(1)}")
                            matched = True
                    if not matched:
                        await context.close()
                        await browser.close()
                        return ExecutorResult(
                            status=ExecutorResultStatus.FAILED,
                            log="script_content 未包含可执行的 page.goto(...)",
                            duration_ms=int((time.time() - start) * 1000),
                        )
                else:
                    await page.goto(base_url)
                    log_lines.append(f"goto {base_url}")

                if env_config.get("screenshot", True):
                    shot = get_screenshots_path() / f"e2e_{uuid.uuid4().hex[:8]}.png"
                    await page.screenshot(path=str(shot), full_page=True)
                    screenshot_url = str(shot)
                    log_lines.append(f"最终截图: {shot}")

                await context.close()
                await browser.close()

            return ExecutorResult(
                status=ExecutorResultStatus.PASSED,
                log="\n".join(log_lines),
                duration_ms=int((time.time() - start) * 1000),
                screenshot_url=screenshot_url,
            )
        except Exception as e:
            log_lines.append(f"E2E 失败: {e}")
            return ExecutorResult(
                status=ExecutorResultStatus.FAILED,
                log="\n".join(log_lines),
                duration_ms=int((time.time() - start) * 1000),
                screenshot_url=screenshot_url,
            )
