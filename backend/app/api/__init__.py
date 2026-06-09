from fastapi import APIRouter
from app.api import auth, projects, test_points, test_cases, test_plans, agents, ai_models, knowledge, workflows, executions, ai_hub_api, users, requirements, reports, dashboard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目"])
api_router.include_router(test_points.router, prefix="/test-points", tags=["测试点"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["需求文档"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["用例"])
api_router.include_router(test_plans.router, prefix="/test-plans", tags=["测试计划"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent"])
api_router.include_router(ai_models.router, prefix="/ai-models", tags=["AI模型"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流"])
api_router.include_router(executions.router, prefix="/executions", tags=["执行"])
api_router.include_router(reports.router, prefix="/reports", tags=["测试报告"])
api_router.include_router(ai_hub_api.router, prefix="/ai-hub", tags=["AI中枢"])
