import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectFeature
from app.models.test_point import TestPoint, TestPointHistory
from app.schemas.test_point import TestPointNode


async def build_tree(db: AsyncSession, project_id: uuid.UUID) -> List[dict]:
    result = await db.execute(
        select(TestPoint)
        .where(TestPoint.project_id == project_id, TestPoint.deleted_at.is_(None))
        .order_by(TestPoint.sort_order)
    )
    nodes = result.scalars().all()
    by_parent: dict = {}
    for n in nodes:
        pid = str(n.parent_id) if n.parent_id else "root"
        meta = n.meta or {}
        by_parent.setdefault(pid, []).append({
            "id": str(n.id),
            "name": n.name,
            "parent_id": str(n.parent_id) if n.parent_id else None,
            "feature_id": str(n.feature_id) if n.feature_id else None,
            "sort_order": n.sort_order,
            "test_type": meta.get("test_type"),
            "locator": meta.get("locator"),
            "children": [],
        })

    def attach(parent_key: str) -> List[dict]:
        items = by_parent.get(parent_key, [])
        for item in items:
            item["children"] = attach(item["id"])
        return items

    return attach("root")


def _collect_tree_ids(nodes: List[TestPointNode]) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for node in nodes:
        if node.id:
            ids.add(node.id)
        if node.children:
            ids |= _collect_tree_ids(node.children)
    return ids


async def save_tree(
    db: AsyncSession,
    project_id: uuid.UUID,
    tree: List[TestPointNode],
    user_id: Optional[uuid.UUID],
    remark: Optional[str] = None,
) -> None:
    from datetime import datetime

    now = datetime.utcnow()
    result = await db.execute(select(TestPoint).where(TestPoint.project_id == project_id))
    existing_by_id = {n.id: n for n in result.scalars().all()}
    keep_ids = _collect_tree_ids(tree)

    for n in existing_by_id.values():
        if n.deleted_at is None and n.id not in keep_ids:
            n.deleted_at = now

    async def upsert_nodes(nodes: List[TestPointNode], parent_id: Optional[uuid.UUID], depth: int):
        for i, node in enumerate(nodes):
            nid = node.id or uuid.uuid4()
            meta: dict = {}
            if node.test_type:
                meta["test_type"] = node.test_type
            if node.locator:
                loc = node.locator.model_dump() if hasattr(node.locator, "model_dump") else node.locator
                if isinstance(loc, dict) and (loc.get("value") or loc.get("description")):
                    meta["locator"] = loc
            if nid in existing_by_id:
                tp = existing_by_id[nid]
                tp.parent_id = parent_id
                tp.name = node.name
                tp.sort_order = node.sort_order or i
                tp.depth = depth
                tp.feature_id = node.feature_id
                tp.meta = meta or None
                tp.deleted_at = None
                tp.updated_at = now
            else:
                tp = TestPoint(
                    id=nid,
                    project_id=project_id,
                    parent_id=parent_id,
                    name=node.name,
                    sort_order=node.sort_order or i,
                    depth=depth,
                    feature_id=node.feature_id,
                    meta=meta or None,
                    created_by=user_id,
                )
                db.add(tp)
                existing_by_id[nid] = tp
            await db.flush()
            if node.children:
                await upsert_nodes(node.children, tp.id, depth + 1)

    await upsert_nodes(tree, None, 0)
    snapshot = await build_tree(db, project_id)
    history = TestPointHistory(
        project_id=project_id,
        tree_snapshot={"tree": snapshot},
        created_by=user_id,
        remark=remark,
    )
    db.add(history)


async def get_leaf_points(db: AsyncSession, project_id: uuid.UUID, point_ids: List[uuid.UUID]) -> List[TestPoint]:
    result = await db.execute(
        select(TestPoint).where(
            TestPoint.project_id == project_id,
            TestPoint.id.in_(point_ids),
            TestPoint.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


def get_root_modules(tree: List[dict]) -> List[dict]:
    """取测试点树顶层模块节点（跳过单一根节点包装）"""
    if not tree:
        return []
    if len(tree) == 1 and tree[0].get("children"):
        return tree[0]["children"]
    return tree


def remove_node_from_tree(tree: List[dict], point_id: str) -> List[dict]:
    """从树中移除指定节点及其子树"""
    result: List[dict] = []
    for node in tree:
        if node.get("id") == point_id:
            continue
        new_node = {**node, "children": remove_node_from_tree(node.get("children") or [], point_id)}
        result.append(new_node)
    return result


def dict_to_nodes(items: List[dict]) -> List[TestPointNode]:
    def to_node(d: dict) -> TestPointNode:
        from app.schemas.test_point import ElementLocator

        locator = d.get("locator")
        loc_obj = ElementLocator(**locator) if isinstance(locator, dict) and locator else None
        return TestPointNode(
            id=uuid.UUID(d["id"]) if d.get("id") else None,
            name=d["name"],
            feature_id=uuid.UUID(d["feature_id"]) if d.get("feature_id") else None,
            sort_order=d.get("sort_order") or 0,
            test_type=d.get("test_type"),
            locator=loc_obj,
            children=[to_node(c) for c in d.get("children") or []],
        )

    return [to_node(x) for x in items]


def wrap_tree_for_save(tree: List[dict], modules: List[dict]) -> List[dict]:
    """若原树有单一根包装，写回 modules 到其 children"""
    if len(tree) == 1 and tree[0].get("children") is not None and not tree[0].get("parent_id"):
        root = {**tree[0], "children": modules}
        return [root]
    return modules


def _tree_has_id(nodes: List[dict], point_id: str) -> bool:
    for n in nodes:
        if n.get("id") == point_id:
            return True
        if _tree_has_id(n.get("children") or [], point_id):
            return True
    return False


async def delete_test_point_node(
    db: AsyncSession,
    project_id: uuid.UUID,
    point_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
) -> bool:
    tree = await build_tree(db, project_id)
    pid = str(point_id)
    if not tree or not _tree_has_id(tree, pid):
        return False
    new_tree = remove_node_from_tree(tree, pid)
    await save_tree(db, project_id, dict_to_nodes(new_tree), user_id, "删除测试点")
    return True


async def rename_root_module(
    db: AsyncSession,
    project_id: uuid.UUID,
    old_name: str,
    new_name: str,
    user_id: Optional[uuid.UUID],
) -> None:
    tree = await build_tree(db, project_id)
    modules = get_root_modules(tree)
    for m in modules:
        if m.get("name") == old_name:
            m["name"] = new_name
    to_save = wrap_tree_for_save(tree, modules)
    await save_tree(db, project_id, dict_to_nodes(to_save), user_id, "重命名功能模块")


async def remove_root_module_by_name(
    db: AsyncSession,
    project_id: uuid.UUID,
    feature_name: str,
    user_id: Optional[uuid.UUID],
) -> None:
    tree = await build_tree(db, project_id)
    modules = [m for m in get_root_modules(tree) if m.get("name") != feature_name]
    to_save = wrap_tree_for_save(tree, modules)
    await save_tree(db, project_id, dict_to_nodes(to_save), user_id, "删除功能及测试点")


async def get_features_text(db: AsyncSession, project_id: uuid.UUID) -> str:
    result = await db.execute(
        select(ProjectFeature).where(ProjectFeature.project_id == project_id)
    )
    features = result.scalars().all()
    return "\n".join(f"- {f.feature_name}: {f.description or ''}" for f in features)
