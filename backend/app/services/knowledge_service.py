"""知识库服务：条目 CRUD、检索、Agent 上下文构建"""
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.data.knowledge_presets import PLATFORM_KNOWLEDGE_BASE
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeEntry

settings = get_settings()


def _score_text(text: str, query: str) -> float:
    if not query.strip():
        return 0.0
    lower_text, lower_q = text.lower(), query.lower()
    tokens = [t for t in re.split(r"\s+", lower_q) if len(t) >= 2]
    if not tokens:
        tokens = [lower_q]
    hits = sum(lower_text.count(t) for t in tokens)
    return min(0.99, 0.3 + hits * 0.15)


async def list_knowledge_bases(
    db: AsyncSession,
    project_id: Optional[UUID] = None,
    include_global: bool = True,
) -> list[KnowledgeBase]:
    q = select(KnowledgeBase)
    if project_id and include_global:
        q = q.where(or_(KnowledgeBase.project_id == project_id, KnowledgeBase.is_global.is_(True)))
    elif project_id:
        q = q.where(KnowledgeBase.project_id == project_id)
    q = q.order_by(KnowledgeBase.created_at.desc())
    return (await db.execute(q)).scalars().all()


async def kb_entry_count(db: AsyncSession, kb_id: UUID) -> int:
    return (
        await db.execute(select(func.count()).select_from(KnowledgeEntry).where(KnowledgeEntry.kb_id == kb_id))
    ).scalar() or 0


async def kb_doc_count(db: AsyncSession, kb_id: UUID) -> int:
    return (
        await db.execute(select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id))
    ).scalar() or 0


async def search_entries(
    db: AsyncSession,
    kb_ids: List[UUID],
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not kb_ids:
        return []
    entries = (
        await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.kb_id.in_(kb_ids))
            .order_by(KnowledgeEntry.sort_order, KnowledgeEntry.updated_at.desc())
        )
    ).scalars().all()
    scored = []
    for e in entries:
        blob = f"{e.title}\n{e.content}"
        score = _score_text(blob, query)
        if score > 0.3 or not query.strip():
            snippet = e.content[:400].replace("\n", " ")
            scored.append(
                {
                    "entry_id": str(e.id),
                    "kb_id": str(e.kb_id),
                    "title": e.title,
                    "category": e.category,
                    "snippet": snippet,
                    "score": round(score, 3),
                }
            )
    scored.sort(key=lambda x: x["score"], reverse=True)
    if query.strip():
        return scored[:top_k]
    return scored[:top_k]


async def build_kb_context(
    db: AsyncSession,
    kb_ids: Optional[List[UUID]] = None,
    project_id: Optional[UUID] = None,
    query: str = "",
    top_k: int = 6,
) -> str:
    """为 Agent 生成注入知识库上下文"""
    ids = list(kb_ids or [])
    if not ids:
        kbs = await list_knowledge_bases(db, project_id=project_id, include_global=True)
        ids = [kb.id for kb in kbs]
    if not ids:
        return ""
    hits = await search_entries(db, ids, query, top_k=top_k)
    if not hits and query:
        hits = await search_entries(db, ids, "", top_k=top_k)
    if not hits:
        return ""
    parts = []
    for h in hits:
        parts.append(f"### {h['title']}（{h['category']}）\n{h['snippet']}")
    return "\n\n".join(parts)


async def seed_knowledge_bases(db: AsyncSession) -> None:
    """预置平台规范知识库"""
    preset = PLATFORM_KNOWLEDGE_BASE
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == preset["name"]))
    kb = result.scalar_one_or_none()
    if not kb:
        kb = KnowledgeBase(
            name=preset["name"],
            description=preset["description"],
            is_global=preset["is_global"],
            chunk_size=settings.kb_chunk_size,
            chunk_overlap=settings.kb_chunk_overlap,
            embedding_model=settings.kb_embedding_model,
        )
        db.add(kb)
        await db.flush()

    for item in preset["entries"]:
        exists = await db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb.id,
                KnowledgeEntry.title == item["title"],
            )
        )
        entry = exists.scalar_one_or_none()
        if not entry:
            db.add(
                KnowledgeEntry(
                    kb_id=kb.id,
                    title=item["title"],
                    category=item["category"],
                    content=item["content"],
                    sort_order=item.get("sort_order", 0),
                )
            )
        else:
            entry.content = item["content"]
            entry.category = item["category"]
            entry.sort_order = item.get("sort_order", entry.sort_order)
            entry.updated_at = datetime.utcnow()
