import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.permissions import require_permission, EDIT_TEST_POINT
from app.database import get_db
from app.models.agent import AgentType
from app.models.test_case import CasePriority, TestCase, TestCaseType
from app.models.test_point import TestPointHistory
from app.models.user import User
from app.schemas.test_point import (
    GenerateCasesFromPointsRequest, GenerateTestPointsRequest,
    TestPointNode, TestPointTreeSave,
)
from app.services import test_point_service
from app.services.feature_service import sync_features_from_test_points
from app.services.agent_runner import AgentRunner, get_agent_or_default
from app.services.ai_hub import AIModelError
from app.services.knowledge_service import build_kb_context
from app.services.requirement_service import get_merged_requirements_text, truncate_requirements

router = APIRouter()


def _normalize_tree(tree, default_test_type: str | None = None) -> list[TestPointNode]:
    from app.schemas.test_point import ElementLocator

    roots = tree if isinstance(tree, list) else ([tree] if isinstance(tree, dict) else [])

    def _locator(raw: dict):
        loc = raw.get("locator")
        if not isinstance(loc, dict):
            return None
        if not (loc.get("value") or loc.get("description")):
            return None
        return ElementLocator(
            strategy=loc.get("strategy") or "css",
            value=loc.get("value") or "",
            description=loc.get("description"),
        )

    def to_node(raw, inherited_type: str | None) -> TestPointNode:
        if isinstance(raw, dict):
            name, children = raw.get("name") or "未命名", raw.get("children") or []
            test_type = raw.get("test_type") or inherited_type or default_test_type
            locator = _locator(raw)
        else:
            name, children = raw.name, raw.children or []
            test_type = getattr(raw, "test_type", None) or inherited_type or default_test_type
            locator = getattr(raw, "locator", None)
        child_type = test_type or inherited_type or default_test_type
        return TestPointNode(
            name=name,
            test_type=test_type,
            locator=locator,
            children=[to_node(c, child_type) for c in children],
        )

    return [to_node(r, default_test_type) for r in roots]


@router.get("/tree/{project_id}")
async def get_tree(project_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tree = await test_point_service.build_tree(db, project_id)
    return {"tree": tree}


@router.post("/tree/save")
async def save_tree(
    data: TestPointTreeSave,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    await test_point_service.save_tree(db, data.project_id, data.tree, user.id, data.remark)
    feat = await sync_features_from_test_points(db, data.project_id)
    return {"message": "测试点树已保存", "features_sync": feat}


@router.post("/generate")
async def generate_test_points(
    data: GenerateTestPointsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    req_text = await get_merged_requirements_text(db, data.project_id, data.document_ids)
    if data.requirements_text:
        req_text = f"{req_text}\n\n{data.requirements_text}".strip()
    if not req_text:
        raise HTTPException(
            400,
            "请先上传需求文档（text/url/pdf/word/md/txt）或填写补充说明",
        )
    req_text, req_truncated = truncate_requirements(req_text)

    try:
        features_text = await test_point_service.get_features_text(db, data.project_id)
        agent_id = await get_agent_or_default(db, data.agent_id, AgentType.DESIGN, data.project_id)
        kb_context = await build_kb_context(
            db, kb_ids=data.kb_ids, project_id=data.project_id, query=req_text[:2000]
        )
        runner = AgentRunner(db, agent_id)
        await runner.load()
        tree = await runner.generate_test_points(
            req_text,
            features_text,
            kb_context,
            test_point_type=data.test_point_type,
            web_page_url=data.web_page_url or "",
            web_locator_hint=data.web_locator_hint or "",
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AIModelError as e:
        raise HTTPException(502, str(e))

    await test_point_service.save_tree(
        db,
        data.project_id,
        _normalize_tree(tree, default_test_type=data.test_point_type),
        user.id,
        f"AI生成({data.test_point_type})",
    )
    feat = await sync_features_from_test_points(db, data.project_id)
    saved = await test_point_service.build_tree(db, data.project_id)
    msg = f"智能体 [{runner._agent.name}] 已生成测试点并同步功能"
    if req_truncated:
        msg += "（需求文档较长，已自动截断后分析）"
    return {
        "tree": saved,
        "agent_id": str(agent_id),
        "message": msg,
        "features_sync": feat,
        "requirements_truncated": req_truncated,
    }


@router.post("/generate-cases")
async def generate_cases_from_points(
    data: GenerateCasesFromPointsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    points = await test_point_service.get_leaf_points(db, data.project_id, data.test_point_ids)
    if not points:
        raise HTTPException(400, "未找到有效测试点")

    if not data.document_ids:
        req_text = await get_merged_requirements_text(db, data.project_id, None)
    else:
        req_text = await get_merged_requirements_text(db, data.project_id, data.document_ids)
    req_text, _ = truncate_requirements(req_text)
    try:
        agent_id = await get_agent_or_default(db, data.agent_id, AgentType.DESIGN, data.project_id)
        kb_context = await build_kb_context(db, project_id=data.project_id, query=req_text[:2000])
        runner = AgentRunner(db, agent_id)
        await runner.load()
    except ValueError as e:
        raise HTTPException(400, str(e))

    created = []
    type_result = await db.execute(select(TestCaseType).where(TestCaseType.name == "功能"))
    default_type = type_result.scalar_one_or_none()

    sem = asyncio.Semaphore(3)

    async def generate_for_point(pt):
        async with sem:
            cases_data = await runner.generate_cases(pt.name, req_text, kb_context)
            return pt, cases_data

    try:
        results = await asyncio.gather(*[generate_for_point(pt) for pt in points])
        for pt, cases_data in results:
            for cd in cases_data:
                tc = TestCase(
                    project_id=data.project_id,
                    version_id=data.version_id,
                    test_point_id=pt.id,
                    name=cd.get("name", f"{pt.name}-用例"),
                    precondition=cd.get("precondition"),
                    steps=cd.get("steps"),
                    expected_result=cd.get("expected_result"),
                    priority=CasePriority(cd.get("priority", "P2"))
                    if cd.get("priority") in ["P0", "P1", "P2", "P3"]
                    else CasePriority.P2,
                    created_by=user.id,
                )
                if default_type:
                    tc.types.append(default_type)
                db.add(tc)
                created.append(tc.name)
    except AIModelError as e:
        raise HTTPException(502, str(e))
    await db.flush()
    return {
        "created_count": len(created),
        "cases": created,
        "agent_id": str(agent_id),
        "message": f"智能体已生成 {len(created)} 条用例",
    }


@router.delete("/node/{point_id}")
async def delete_test_point_node(
    point_id: UUID,
    project_id: UUID = Query(..., description="项目 ID"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_TEST_POINT)),
):
    ok = await test_point_service.delete_test_point_node(db, project_id, point_id, user.id)
    if not ok:
        raise HTTPException(404, "测试点不存在")
    feat = await sync_features_from_test_points(db, project_id)
    return {"message": "测试点已删除", "features_sync": feat}


@router.get("/history/{project_id}")
async def list_history(project_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(
        select(TestPointHistory).where(TestPointHistory.project_id == project_id).order_by(TestPointHistory.created_at.desc())
    )
    return result.scalars().all()
