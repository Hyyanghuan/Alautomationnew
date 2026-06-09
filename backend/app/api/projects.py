import math
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.permissions import require_permission, CREATE_PROJECT, EDIT_FEATURE
from app.database import get_db
from app.models.project import Project, ProjectFeature, ProjectStatus, ProjectVersion, VersionStatus
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.project import (
    FeatureCreate, FeatureDetailOut, FeatureOut, FeatureUpdate,
    ProjectCreate, ProjectOut, ProjectStatusChange, ProjectUpdate,
    VersionCreate, VersionOut, VersionStatusChange, VersionUpdate,
)
from app.services import test_point_service
from app.services.feature_service import (
    delete_feature_cascade,
    get_features_with_test_points,
    sync_features_from_test_points,
)

router = APIRouter()

# 状态流转：启动 / 暂停 / 挂起 / 完成
_STATUS_TRANSITIONS: dict[str, dict] = {
    "start": {
        "target": ProjectStatus.ACTIVE,
        "allowed": {ProjectStatus.PLANNING, ProjectStatus.PAUSED, ProjectStatus.SUSPENDED},
        "msg": "仅规划中、已暂停、已挂起的项目可启动",
    },
    "pause": {
        "target": ProjectStatus.PAUSED,
        "allowed": {ProjectStatus.ACTIVE},
        "msg": "仅进行中的项目可暂停",
    },
    "suspend": {
        "target": ProjectStatus.SUSPENDED,
        "allowed": {ProjectStatus.ACTIVE, ProjectStatus.PAUSED},
        "msg": "仅进行中或已暂停的项目可挂起",
    },
    "complete": {
        "target": ProjectStatus.COMPLETED,
        "allowed": {ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.PAUSED, ProjectStatus.SUSPENDED},
        "msg": "已完成或已归档的项目不能再次完成",
    },
    "restart": {
        "target": ProjectStatus.ACTIVE,
        "allowed": {ProjectStatus.PAUSED, ProjectStatus.SUSPENDED, ProjectStatus.COMPLETED},
        "msg": "仅已暂停、已挂起、已完成的项目可重启",
    },
}

_VERSION_TRANSITIONS: dict[str, dict] = {
    "start": {
        "target": VersionStatus.DEVELOPING,
        "allowed": {VersionStatus.PLANNING, VersionStatus.SUSPENDED},
        "msg": "仅规划中、已挂起的版本可启动",
    },
    "suspend": {
        "target": VersionStatus.SUSPENDED,
        "allowed": {VersionStatus.DEVELOPING, VersionStatus.TESTING},
        "msg": "仅开发中、测试中的版本可挂起",
    },
    "complete": {
        "target": VersionStatus.RELEASED,
        "allowed": {VersionStatus.PLANNING, VersionStatus.DEVELOPING, VersionStatus.TESTING, VersionStatus.SUSPENDED},
        "msg": "已发布的版本不能再次完成",
    },
}


async def _get_project_or_404(project_id: UUID, db: AsyncSession) -> Project:
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    return p


@router.get("", response_model=PageResult[ProjectOut])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Project)
    if keyword:
        q = q.where(Project.name.ilike(f"%{keyword}%"))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    result = await db.execute(
        q.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    return PageResult(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)))


@router.post("", response_model=ProjectOut)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PROJECT)),
):
    p = Project(**data.model_dump(), created_by=user.id)
    db.add(p)
    await db.flush()
    return p


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    return p


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID, data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(CREATE_PROJECT)),
):
    p = await _get_project_or_404(project_id, db)
    payload = data.model_dump(exclude_unset=True)
    if p.status in (ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED) and payload.get("status") not in (
        None, ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED
    ):
        raise HTTPException(400, "已完成或已归档的项目不可变更状态")
    if "start_date" in payload and "end_date" in payload:
        sd, ed = payload.get("start_date"), payload.get("end_date")
        if sd and ed and sd > ed:
            raise HTTPException(400, "开始时间不能晚于结束时间")
    elif "start_date" in payload and p.end_date and payload["start_date"] > p.end_date:
        raise HTTPException(400, "开始时间不能晚于结束时间")
    elif "end_date" in payload and p.start_date and payload["end_date"] < p.start_date:
        raise HTTPException(400, "结束时间不能早于开始时间")
    for k, v in payload.items():
        setattr(p, k, v)
    return p


@router.post("/{project_id}/status", response_model=ProjectOut)
async def change_project_status(
    project_id: UUID,
    data: ProjectStatusChange,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(CREATE_PROJECT)),
):
    p = await _get_project_or_404(project_id, db)
    rule = _STATUS_TRANSITIONS.get(data.action)
    if not rule:
        raise HTTPException(400, "无效操作")
    if data.action != "restart" and p.status in (ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED):
        raise HTTPException(400, "已完成或已归档的项目不可变更状态")
    if p.status not in rule["allowed"]:
        raise HTTPException(400, rule["msg"])
    p.status = rule["target"]
    return p


@router.get("/{project_id}/versions", response_model=list[VersionOut])
async def list_versions(project_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(ProjectVersion).where(ProjectVersion.project_id == project_id))
    return result.scalars().all()


@router.post("/{project_id}/versions", response_model=VersionOut)
async def create_version(
    project_id: UUID, data: VersionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(CREATE_PROJECT)),
):
    v = ProjectVersion(project_id=project_id, **data.model_dump())
    db.add(v)
    await db.flush()
    return v


@router.put("/versions/{version_id}", response_model=VersionOut)
async def update_version(
    version_id: UUID,
    data: VersionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(CREATE_PROJECT)),
):
    v = await db.get(ProjectVersion, version_id)
    if not v:
        raise HTTPException(404, "版本不存在")
    for k, val in data.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    return v


@router.post("/versions/{version_id}/status", response_model=VersionOut)
async def change_version_status(
    version_id: UUID,
    data: VersionStatusChange,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(CREATE_PROJECT)),
):
    v = await db.get(ProjectVersion, version_id)
    if not v:
        raise HTTPException(404, "版本不存在")
    rule = _VERSION_TRANSITIONS.get(data.action)
    if not rule:
        raise HTTPException(400, "无效操作")
    if v.status == VersionStatus.RELEASED:
        raise HTTPException(400, "已发布的版本不可变更状态")
    if v.status not in rule["allowed"]:
        raise HTTPException(400, rule["msg"])
    v.status = rule["target"]
    return v


@router.post("/{project_id}/features/sync-from-test-points")
async def sync_features(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_FEATURE)),
):
    await _get_project_or_404(project_id, db)
    return await sync_features_from_test_points(db, project_id)


@router.get("/{project_id}/features", response_model=list[FeatureOut])
async def list_features(
    project_id: UUID,
    introduced_version: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(ProjectFeature).where(ProjectFeature.project_id == project_id)
    if introduced_version:
        q = q.where(ProjectFeature.introduced_version == introduced_version)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/{project_id}/features", response_model=FeatureOut)
async def create_feature(
    project_id: UUID, data: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_FEATURE)),
):
    f = ProjectFeature(project_id=project_id, **data.model_dump())
    db.add(f)
    await db.flush()
    return f


@router.get("/{project_id}/features/detail", response_model=list[FeatureDetailOut])
async def list_features_detail(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_project_or_404(project_id, db)
    return await get_features_with_test_points(db, project_id)


@router.put("/features/{feature_id}", response_model=FeatureOut)
async def update_feature(
    feature_id: UUID,
    data: FeatureUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_FEATURE)),
):
    f = await db.get(ProjectFeature, feature_id)
    if not f:
        raise HTTPException(404, "功能不存在")
    old_name = f.feature_name
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    if data.feature_name and data.feature_name != old_name:
        await test_point_service.rename_root_module(
            db, f.project_id, old_name, data.feature_name, user.id
        )
    await db.flush()
    return f


@router.delete("/features/{feature_id}")
async def delete_feature(
    feature_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_FEATURE)),
):
    f = await delete_feature_cascade(db, feature_id, user.id)
    if not f:
        raise HTTPException(404, "功能不存在")
    feat = await sync_features_from_test_points(db, f.project_id)
    return {"message": f"已删除功能「{f.feature_name}」及其测试点", "features_sync": feat}
