"""Playwright Google Chrome 浏览器下载与路径管理"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_MARKER = ".chrome_ready"


def get_browsers_path() -> Path:
    """浏览器二进制存放目录（可通过 PLAYWRIGHT_BROWSERS_PATH 配置）"""
    env_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_path:
        root = Path(env_path)
    else:
        candidates = [
            Path("/app/data/browsers"),
            Path(__file__).resolve().parent.parent.parent / "data" / "browsers",
        ]
        root = next((c for c in candidates if c.parent.exists()), candidates[-1])
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_screenshots_path() -> Path:
    env_path = os.getenv("PLAYWRIGHT_SCREENSHOTS_PATH", "").strip()
    root = Path(env_path) if env_path else get_browsers_path().parent / "screenshots"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_chrome_ready() -> Path:
    """
    确保 Google Chrome 已下载到指定目录。
    首次调用会执行: python -m playwright install chrome
    """
    browsers_path = get_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    marker = browsers_path / _MARKER
    if marker.exists():
        return browsers_path

    cmd = [sys.executable, "-m", "playwright", "install", "chrome"]
    env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(browsers_path)}
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    log = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"Chrome 下载失败 (code={proc.returncode}): {log[:500]}")

    marker.write_text(f"installed\npath={browsers_path}\n", encoding="utf-8")
    return browsers_path


def chrome_install_info() -> dict:
    path = get_browsers_path()
    marker = path / _MARKER
    return {
        "browsers_path": str(path),
        "screenshots_path": str(get_screenshots_path()),
        "chrome_ready": marker.exists(),
        "marker": str(marker),
    }
