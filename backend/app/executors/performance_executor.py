import asyncio
import statistics
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from app.executors.base import BaseExecutor, ExecutorResult, ExecutorResultStatus


class PerformanceExecutor(BaseExecutor):
    executor_type = "performance"

    async def _single_request(self, client: httpx.AsyncClient, url: str, method: str) -> float:
        t0 = time.perf_counter()
        await client.request(method, url)
        return (time.perf_counter() - t0) * 1000

    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        start = time.time()
        base_url = env_config.get("base_url", "http://localhost:8000")
        steps = case_data.get("steps") or []
        perf_cfg = case_data.get("performance") or {}

        url = perf_cfg.get("url")
        if not url and steps:
            url = steps[0].get("url", "/health")
        if not url:
            url = "/health"
        if not url.startswith("http"):
            url = urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))

        method = (perf_cfg.get("method") or "GET").upper()
        concurrency = int(perf_cfg.get("concurrency") or env_config.get("concurrency", 10))
        total_requests = int(perf_cfg.get("total_requests") or env_config.get("total_requests", 50))
        duration_sec = int(perf_cfg.get("duration_sec") or 0)

        latencies: list[float] = []
        errors = 0
        log_lines = [f"目标: {method} {url}", f"并发: {concurrency}, 总请求: {total_requests}"]

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if duration_sec > 0:
                    deadline = time.time() + duration_sec
                    while time.time() < deadline:
                        batch = [
                            self._single_request(client, url, method)
                            for _ in range(concurrency)
                        ]
                        results = await asyncio.gather(*batch, return_exceptions=True)
                        for r in results:
                            if isinstance(r, Exception):
                                errors += 1
                            else:
                                latencies.append(r)
                else:
                    remaining = total_requests
                    while remaining > 0:
                        batch_size = min(concurrency, remaining)
                        batch = [
                            self._single_request(client, url, method)
                            for _ in range(batch_size)
                        ]
                        results = await asyncio.gather(*batch, return_exceptions=True)
                        for r in results:
                            if isinstance(r, Exception):
                                errors += 1
                            else:
                                latencies.append(r)
                        remaining -= batch_size

            elapsed = max(time.time() - start, 0.001)
            success = len(latencies)
            tps = round(success / elapsed, 2)
            avg_ms = round(statistics.mean(latencies), 2) if latencies else 0
            p95 = round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else avg_ms

            log_lines.extend([
                f"成功: {success}, 失败: {errors}",
                f"TPS: {tps}",
                f"平均延迟: {avg_ms}ms",
                f"P95: {p95}ms",
                f"总耗时: {round(elapsed, 2)}s",
            ])

            threshold_tps = perf_cfg.get("min_tps")
            threshold_latency = perf_cfg.get("max_avg_latency_ms")
            failed = False
            if threshold_tps and tps < threshold_tps:
                log_lines.append(f"未达 TPS 阈值 {threshold_tps}")
                failed = True
            if threshold_latency and avg_ms > threshold_latency:
                log_lines.append(f"超过延迟阈值 {threshold_latency}ms")
                failed = True
            if errors > success * 0.1:
                log_lines.append("错误率超过 10%")
                failed = True

            status = ExecutorResultStatus.FAILED if failed else ExecutorResultStatus.PASSED
            return ExecutorResult(
                status=status,
                log="\n".join(log_lines),
                duration_ms=int((time.time() - start) * 1000),
                extra={"tps": tps, "avg_latency_ms": avg_ms, "p95_ms": p95, "errors": errors, "success": success},
            )
        except Exception as e:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=f"性能测试异常: {e}",
                duration_ms=int((time.time() - start) * 1000),
            )
