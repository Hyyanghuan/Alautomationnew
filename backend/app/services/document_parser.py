"""需求文档解析：text / url / pdf / word / md / txt"""
import re
from pathlib import Path
from typing import Optional

import httpx

from app.models.requirement_doc import DocSourceType

MAX_CHARS = 200_000


async def fetch_url_text(url: str, timeout: int = 30) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if "html" in content_type:
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.I | re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_CHARS]


def parse_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)[:MAX_CHARS]
    except Exception as e:
        return f"[PDF解析失败: {e}]"


def parse_word(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:MAX_CHARS]
    except Exception as e:
        return f"[Word解析失败: {e}]"


def parse_text_file(file_path: str) -> str:
    path = Path(file_path)
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)[:MAX_CHARS]
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")[:MAX_CHARS]


async def extract_content(
    source_type: DocSourceType,
    *,
    text: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
) -> str:
    if source_type == DocSourceType.TEXT:
        return (text or "")[:MAX_CHARS]
    if source_type == DocSourceType.URL:
        if not url:
            raise ValueError("URL 不能为空")
        return await fetch_url_text(url)
    if not file_path:
        raise ValueError("文件路径不能为空")
    if source_type == DocSourceType.PDF:
        return parse_pdf(file_path)
    if source_type == DocSourceType.WORD:
        return parse_word(file_path)
    if source_type in (DocSourceType.MD, DocSourceType.TXT):
        return parse_text_file(file_path)
    return parse_text_file(file_path)
