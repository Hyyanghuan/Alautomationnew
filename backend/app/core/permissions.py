"""RBAC 权限矩阵 - 对应设计文档 4.2"""
from functools import wraps
from typing import Callable, Set

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import Role, User

# 权限操作定义
MANAGE_KB = "manage_knowledge_base"
MANAGE_AI_MODEL = "manage_ai_model"
MANAGE_AGENT_TEMPLATE = "manage_agent_template"
MANAGE_PROJECT_AGENT = "manage_project_agent"
CREATE_PROJECT = "create_project"
EDIT_FEATURE = "edit_feature"
EDIT_TEST_POINT = "edit_test_point"
EDIT_CASE = "edit_case"
EXECUTE_PLAN = "execute_plan"
VIEW_REPORT = "view_report"

ROLE_PERMISSIONS: dict[Role, Set[str]] = {
    Role.SUPER_ADMIN: {
        MANAGE_KB, MANAGE_AI_MODEL, MANAGE_AGENT_TEMPLATE, MANAGE_PROJECT_AGENT,
        CREATE_PROJECT, EDIT_FEATURE, EDIT_TEST_POINT, EDIT_CASE, EXECUTE_PLAN, VIEW_REPORT,
    },
    Role.ADMIN: {
        MANAGE_KB, MANAGE_AI_MODEL, MANAGE_AGENT_TEMPLATE, MANAGE_PROJECT_AGENT,
        CREATE_PROJECT, EDIT_FEATURE, EDIT_TEST_POINT, EDIT_CASE, EXECUTE_PLAN, VIEW_REPORT,
    },
    Role.PROJECT_MANAGER: {
        MANAGE_PROJECT_AGENT, CREATE_PROJECT, EDIT_FEATURE,
        EDIT_TEST_POINT, EDIT_CASE, EXECUTE_PLAN, VIEW_REPORT,
    },
    Role.TEST_MANAGER: {
        EDIT_FEATURE, EDIT_TEST_POINT, EDIT_CASE, EXECUTE_PLAN, VIEW_REPORT,
    },
    Role.TEST_ENGINEER: {
        EDIT_TEST_POINT, EDIT_CASE, EXECUTE_PLAN, VIEW_REPORT,
    },
    Role.VIEWER: {VIEW_REPORT},
}


def has_permission(user: User, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def require_permission(permission: str):
    async def checker(user: User = Depends(get_current_user)):
        if not has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user
    return checker


def require_roles(*roles: Role):
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色权限不足")
        return user
    return checker
