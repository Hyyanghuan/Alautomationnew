import asyncio
import os
import tempfile
import time
from pathlib import Path

from app.executors.base import BaseExecutor, ExecutorResult, ExecutorResultStatus


class UnitExecutor(BaseExecutor):
    executor_type = "unit"

    async def execute(self, case_data: dict, env_config: dict) -> ExecutorResult:
        start = time.time()
        script = (case_data.get("script_content") or "").strip()
        if not script:
            return ExecutorResult(
                status=ExecutorResultStatus.SKIPPED,
                log="无 script_content，单元测试跳过",
                duration_ms=int((time.time() - start) * 1000),
            )

        timeout = int(env_config.get("pytest_timeout", 120))
        work_dir = Path(tempfile.mkdtemp(prefix="unit_test_"))
        test_file = work_dir / "test_case.py"
        test_file.write_text(script, encoding="utf-8")

        env = os.environ.copy()
        for k, v in (env_config.get("env") or {}).items():
            env[str(k)] = str(v)

        cmd = ["python", "-m", "pytest", str(test_file), "-v", "--tb=short"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = (stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")).strip()
            duration_ms = int((time.time() - start) * 1000)
            if proc.returncode == 0:
                return ExecutorResult(
                    status=ExecutorResultStatus.PASSED,
                    log=out or "pytest 通过",
                    duration_ms=duration_ms,
                )
            return ExecutorResult(
                status=ExecutorResultStatus.FAILED,
                log=out or f"pytest 退出码 {proc.returncode}",
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=f"pytest 超时 ({timeout}s)",
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return ExecutorResult(
                status=ExecutorResultStatus.ERROR,
                log=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )
        finally:
            try:
                test_file.unlink(missing_ok=True)
                work_dir.rmdir()
            except OSError:
                pass
