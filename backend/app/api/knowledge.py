from datetime import datetime
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.permissions import require_permission, MANAGE_KB
from app.config import get_settings
from app.database import get_db
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeEntry
from app.models.user import User
from app.services import knowledge_service

router = APIRouter()
settings = get_settings()


class KBCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    is_global: bool = False


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    is_global: Optional[bool] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


class EntryCreate(BaseModel):
    title: str
    category: str = "custom"
    content: str
    sort_order: int = 0


class EntryUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    sort_order: Optional[int] = None


class SearchRequest(BaseModel):
    kb_id: Optional[UUID] = None
    kb_ids: Optional[List[UUID]] = None
    query: str = ""
    top_k: int = 5


async def _kb_out(kb: KnowledgeBase, db: AsyncSession) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "project_id": kb.project_id,
        "is_global": kb.is_global,
        "chunk_size": kb.chunk_size,
        "chunk_overlap": kb.chunk_overlap,
        "embedding_model": kb.embedding_model,
        "created_at": kb.created_at,
        "entry_count": await knowledge_service.kb_entry_count(db, kb.id),
        "document_count": await knowledge_service.kb_doc_count(db, kb.id),
    }


@router.get("")
async def list_kb(
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """列出知识库（测试点生成等页面可选）"""
    kbs = await knowledge_service.list_knowledge_bases(db, project_id=project_id)
    return [await _kb_out(kb, db) for kb in kbs]


@router.get("/manage")
async def list_kb_manage(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    kbs = result.scalars().all()
    return [await _kb_out(kb, db) for kb in kbs]


@router.post("")
async def create_kb(
    data: KBCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    kb = KnowledgeBase(
        **data.model_dump(),
        chunk_size=settings.kb_chunk_size,
        chunk_overlap=settings.kb_chunk_overlap,
        embedding_model=settings.kb_embedding_model,
    )
    db.add(kb)
    await db.flush()
    return await _kb_out(kb, db)


@router.get("/{kb_id}")
async def get_kb(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    return await _kb_out(kb, db)


@router.put("/{kb_id}")
async def update_kb(
    kb_id: UUID,
    data: KBUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(kb, k, v)
    return await _kb_out(kb, db)


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    await db.delete(kb)
    return {"message": "知识库已删除"}


@router.get("/{kb_id}/entries")
async def list_entries(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.kb_id == kb_id)
        .order_by(KnowledgeEntry.sort_order, KnowledgeEntry.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/{kb_id}/entries")
async def create_entry(
    kb_id: UUID,
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    entry = KnowledgeEntry(kb_id=kb_id, **data.model_dump())
    db.add(entry)
    await db.flush()
    return entry


@router.put("/{kb_id}/entries/{entry_id}")
async def update_entry(
    kb_id: UUID,
    entry_id: UUID,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    entry = await db.get(KnowledgeEntry, entry_id)
    if not entry or entry.kb_id != kb_id:
        raise HTTPException(404, "条目不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    entry.updated_at = datetime.utcnow()
    return entry


@router.delete("/{kb_id}/entries/{entry_id}")
async def delete_entry(
    kb_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    entry = await db.get(KnowledgeEntry, entry_id)
    if not entry or entry.kb_id != kb_id:
        raise HTTPException(404, "条目不存在")
    await db.delete(entry)
    return {"message": "条目已删除"}


@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id).order_by(KnowledgeDocument.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{kb_id}/upload")
async def upload_document(
    kb_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_KB)),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    content = await file.read()
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    chunks = [
        text[i : i + settings.kb_chunk_size]
        for i in range(0, max(len(text), 1), max(settings.kb_chunk_size - settings.kb_chunk_overlap, 1))
    ] if text else []
    doc = KnowledgeDocument(
        kb_id=kb_id,
        filename=file.filename or "unknown",
        file_type=file.content_type,
        chunk_count=len(chunks),
        status="indexed",
        meta={"size": len(content), "text_length": len(text)},
    )
    db.add(doc)
    if text.strip():
        db.add(
            KnowledgeEntry(
                kb_id=kb_id,
                title=f"文档：{file.filename}",
                category="upload",
                content=text[:50000],
                sort_order=999,
            )
        )
    await db.flush()
    return {"filename": file.filename, "chunks": len(chunks), "status": "indexed", "entry_created": bool(text.strip())}


@router.post("/search")
async def search_kb(
    data: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    kb_ids: List[UUID] = list(data.kb_ids or [])
    if data.kb_id:
        kb_ids.append(data.kb_id)
    if not kb_ids:
        kbs = await knowledge_service.list_knowledge_bases(db)
        kb_ids = [kb.id for kb in kbs]
    results = await knowledge_service.search_entries(db, kb_ids, data.query, data.top_k)
    return {"query": data.query, "results": results}
