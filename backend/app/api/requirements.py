import uuid as uuid_mod
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.permissions import require_permission, EDIT_TEST_POINT
from app.database import get_db
from app.models.requirement_doc import DocSourceType, RequirementDocument
from app.models.user import User
from app.services.document_parser import extract_content
from app.services.requirement_service import ensure_upload_dir

router = APIRouter()

ALLOWED_EXT = {
    ".pdf": DocSourceType.PDF,
    ".doc": DocSourceType.WORD,
    ".docx": DocSourceType.WORD,
    ".md": DocSourceType.MD,
    ".markdown": DocSourceType.MD,
    ".txt": DocSourceType.TXT,
}


class TextUploadRequest(BaseModel):
    project_id: UUID
    content: str
    title: str | None = None


class UrlUploadRequest(BaseModel):
    project_id: UUID
    url: str
    title: str | None = None


def _auto_title(prefix: str, hint: str = "") -> str:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    suffix = f"-{hint}" if hint else ""
    return f"{prefix}{suffix}-{ts}"


class RequirementDocOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    source_type: DocSourceType
    source_url: str | None
    filename: str | None
    char_count: int
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/{project_id}")
async def list_documents(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RequirementDocument)
        .where(RequirementDocument.project_id == project_id)
        .order_by(RequirementDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "project_id": d.project_id,
            "title": d.title,
            "source_type": d.source_type.value,
            "source_url": d.source_url,
            "filename": d.filename,
            "char_count": d.char_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/text", response_model=dict)
async def upload_text(
    data: TextUploadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    content = data.content[:200_000]
    doc = RequirementDocument(
        project_id=data.project_id,
        title=data.title or _auto_title("文本需求"),
        source_type=DocSourceType.TEXT,
        content_text=content,
        char_count=len(content),
        created_by=user.id,
    )
    db.add(doc)
    await db.flush()
    return {"id": str(doc.id), "char_count": doc.char_count}


@router.post("/url", response_model=dict)
async def upload_url(
    data: UrlUploadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    try:
        content = await extract_content(DocSourceType.URL, url=data.url)
    except Exception as e:
        raise HTTPException(400, f"URL 抓取失败: {e}")
    from urllib.parse import urlparse
    host = urlparse(data.url).netloc or "链接"
    doc = RequirementDocument(
        project_id=data.project_id,
        title=data.title or _auto_title("URL需求", host[:30]),
        source_type=DocSourceType.URL,
        source_url=data.url,
        content_text=content,
        char_count=len(content),
        created_by=user.id,
    )
    db.add(doc)
    await db.flush()
    return {"id": str(doc.id), "char_count": doc.char_count}


@router.post("/file", response_model=dict)
async def upload_file(
    project_id: UUID = Form(...),
    title: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            400,
            f"不支持格式 {ext}，支持: pdf, doc, docx, md, txt",
        )
    source_type = ALLOWED_EXT[ext]
    upload_dir = ensure_upload_dir(project_id)
    safe_name = f"{uuid_mod.uuid4().hex}{ext}"
    file_path = upload_dir / safe_name
    data = await file.read()
    file_path.write_bytes(data)

    try:
        content = await extract_content(source_type, file_path=str(file_path))
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {e}")

    doc = RequirementDocument(
        project_id=project_id,
        title=title or _auto_title("文件", (file.filename or "文档")[:40]),
        source_type=source_type,
        file_path=str(file_path),
        filename=file.filename,
        content_text=content,
        char_count=len(content),
        created_by=user.id,
    )
    db.add(doc)
    await db.flush()
    return {"id": str(doc.id), "char_count": doc.char_count, "source_type": source_type.value}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    doc = await db.get(RequirementDocument, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    if doc.file_path:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink(missing_ok=True)
    await db.delete(doc)
    return {"message": "已删除"}
