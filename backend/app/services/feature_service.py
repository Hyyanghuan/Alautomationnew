"""从测试点树自动同步项目功能"""
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectFeature
from app.models.test_case import TestCase
from app.services import test_point_service


def _collect_feature_names(nodes: list[Any]) -> list[str]:
    """取测试点树顶层模块名称作为功能（跳过单一根节点包装）"""
    modules = test_point_service.get_root_modules(nodes)
    seen: set[str] = set()
    unique: list[str] = []
    for node in modules:
        name = (node.get("name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


async def sync_features_from_test_points(db: AsyncSession, project_id: uuid.UUID) -> dict:
    tree = await test_point_service.build_tree(db, project_id)
    names = _collect_feature_names(tree)

    result = await db.execute(
        select(ProjectFeature).where(ProjectFeature.project_id == project_id)
    )
    existing_list = list(result.scalars().all())
    existing = {f.feature_name: f for f in existing_list}
    name_set = set(names)

    removed = 0
    for f in existing_list:
        if f.feature_name not in name_set:
            await db.delete(f)
            removed += 1
    await db.flush()

    if not names:
        return {
            "created": 0,
            "removed": removed,
            "total": 0,
            "message": "暂无测试点，已清理孤立功能" if removed else "暂无测试点，无法生成功能",
        }

    result = await db.execute(
        select(ProjectFeature).where(ProjectFeature.project_id == project_id)
    )
    current = {f.feature_name: f for f in result.scalars().all()}
    created = 0
    for name in names:
        if name in current:
            continue
        db.add(
            ProjectFeature(
                project_id=project_id,
                feature_name=name,
                description=f"由测试点「{name}」自动同步",
            )
        )
        created += 1
    await db.flush()
    total = len(name_set)
    parts = []
    if created:
        parts.append(f"新增 {created} 个")
    if removed:
        parts.append(f"移除 {removed} 个")
    msg = f"已从测试点同步功能（共 {total} 个）"
    if parts:
        msg = f"已从测试点同步：{', '.join(parts)}（共 {total} 个）"
    return {
        "created": created,
        "removed": removed,
        "total": total,
        "names": names,
        "message": msg,
    }


def _build_point_feature_map(tree: list[dict]) -> dict[str, str]:
    """测试点 ID -> 顶层功能模块名"""
    mapping: dict[str, str] = {}
    modules = test_point_service.get_root_modules(tree)

    def walk(nodes: list[dict], feature_name: str) -> None:
        for n in nodes:
            nid = n.get("id")
            if nid:
                mapping[str(nid)] = feature_name
            walk(n.get("children") or [], feature_name)

    for mod in modules:
        name = (mod.get("name") or "").strip()
        if not name:
            continue
        if mod.get("id"):
            mapping[str(mod["id"])] = name
        walk(mod.get("children") or [], name)
    return mapping


def _case_summary(case: TestCase) -> dict:
    status = case.status.value if hasattr(case.status, "value") else str(case.status)
    priority = case.priority.value if hasattr(case.priority, "value") else str(case.priority)
    return {
        "id": str(case.id),
        "name": case.name,
        "priority": priority,
        "status": status,
        "type_names": [t.name for t in (case.types or [])],
        "test_point_id": str(case.test_point_id) if case.test_point_id else None,
        "precondition": case.precondition,
        "steps": case.steps,
        "expected_result": case.expected_result,
        "tags": case.tags or [],
        "script_content": case.script_content,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


async def get_features_with_test_points(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    tree = await test_point_service.build_tree(db, project_id)
    modules = test_point_service.get_root_modules(tree)
    point_feature_map = _build_point_feature_map(tree)

    cases_result = await db.execute(
        select(TestCase).where(TestCase.project_id == project_id).order_by(TestCase.updated_at.desc())
    )
    cases_by_feature: dict[str, list[dict]] = {}
    for case in cases_result.scalars().all():
        feat_name = None
        if case.test_point_id:
            feat_name = point_feature_map.get(str(case.test_point_id))
        key = feat_name or "__unlinked__"
        cases_by_feature.setdefault(key, []).append(_case_summary(case))

    result = await db.execute(
        select(ProjectFeature).where(ProjectFeature.project_id == project_id)
    )
    by_name = {f.feature_name: f for f in result.scalars().all()}
    items: list[dict] = []
    seen: set[str] = set()
    for mod in modules:
        name = (mod.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        f = by_name.get(name)
        items.append({
            "id": str(f.id) if f else None,
            "project_id": str(project_id),
            "feature_name": name,
            "description": f.description if f else f"由测试点「{name}」自动同步",
            "introduced_version": f.introduced_version if f else None,
            "removed_version": f.removed_version if f else None,
            "created_at": f.created_at if f else None,
            "updated_at": f.updated_at if f else None,
            "test_points": mod.get("children") or [],
            "test_cases": cases_by_feature.get(name, []),
            "root_point_id": mod.get("id"),
        })
    for f in by_name.values():
        if f.feature_name not in seen:
            items.append({
                "id": str(f.id),
                "project_id": str(f.project_id),
                "feature_name": f.feature_name,
                "description": f.description,
                "introduced_version": f.introduced_version,
                "removed_version": f.removed_version,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
                "test_points": [],
                "test_cases": cases_by_feature.get(f.feature_name, []),
                "root_point_id": None,
            })
    unlinked = cases_by_feature.get("__unlinked__", [])
    if unlinked:
        items.append({
            "id": None,
            "project_id": str(project_id),
            "feature_name": "未关联功能",
            "description": "未绑定测试点的用例",
            "introduced_version": None,
            "removed_version": None,
            "created_at": None,
            "updated_at": None,
            "test_points": [],
            "test_cases": unlinked,
            "root_point_id": None,
        })
    return items


async def delete_feature_cascade(
    db: AsyncSession,
    feature_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
) -> Optional[ProjectFeature]:
    f = await db.get(ProjectFeature, feature_id)
    if not f:
        return None
    await test_point_service.remove_root_module_by_name(db, f.project_id, f.feature_name, user_id)
    await db.delete(f)
    await db.flush()
    return f
