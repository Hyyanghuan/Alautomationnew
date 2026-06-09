from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.requirement_doc import RequirementDocument

settings = get_settings()
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "requirements"
MAX_REQUIREMENT_CHARS = 12000


async def get_merged_requirements_text(
    db: AsyncSession, project_id: UUID, document_ids: list[UUID] | None = None
) -> str:
    q = select(RequirementDocument).where(RequirementDocument.project_id == project_id)
    if document_ids:
        q = q.where(RequirementDocument.id.in_(document_ids))
    result = await db.execute(q.order_by(RequirementDocument.created_at))
    docs = result.scalars().all()
    if not docs:
        return ""
    parts = []
    for d in docs:
        header = f"### [{d.source_type.value}] {d.title}"
        body = d.content_text or ""
        parts.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(parts)


def truncate_requirements(text: str, max_chars: int = MAX_REQUIREMENT_CHARS) -> tuple[str, bool]:
    """截断过长需求，避免大模型输出 token 超限导致 JSON 截断"""
    if len(text) <= max_chars:
        return text, False
    head = max_chars // 2
    tail = max_chars - head - 80
    truncated = (
        text[:head]
        + "\n\n...[中间内容已省略]...\n\n"
        + text[-tail:]
        + f"\n\n[提示：需求原文共 {len(text)} 字，已截断至 {max_chars} 字供 AI 分析]"
    )
    return truncated, True


def ensure_upload_dir(project_id: UUID) -> Path:
    path = UPLOAD_DIR / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path
