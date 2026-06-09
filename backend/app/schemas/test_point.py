from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ElementLocator(BaseModel):
    strategy: str = Field("css", description="css|xpath|id|text|role")
    value: str = ""
    description: Optional[str] = None


class TestPointNode(BaseModel):
    id: Optional[UUID] = None
    name: str
    parent_id: Optional[UUID] = None
    feature_id: Optional[UUID] = None
    sort_order: int = 0
    test_type: Optional[str] = Field(None, description="功能|接口|Web页面|Agent测试")
    locator: Optional[ElementLocator] = None
    children: List["TestPointNode"] = []


TestPointNode.model_rebuild()


class TestPointTreeSave(BaseModel):
    project_id: UUID
    tree: List[TestPointNode]
    remark: Optional[str] = None


class TestPointOut(BaseModel):
    id: UUID
    project_id: UUID
    parent_id: Optional[UUID]
    name: str
    sort_order: int
    depth: int
    feature_id: Optional[UUID]
    test_type: Optional[str] = None
    locator: Optional[dict] = None

    model_config = {"from_attributes": True}


class GenerateTestPointsRequest(BaseModel):
    project_id: UUID
    agent_id: Optional[UUID] = None
    document_ids: Optional[List[UUID]] = Field(None, description="关联需求文档ID，至少选一个或上传文档")
    kb_ids: Optional[List[UUID]] = Field(None, description="引用知识库ID，不选则自动使用全局+项目知识库")
    feature_ids: Optional[List[UUID]] = None
    requirements_text: Optional[str] = None
    test_point_type: str = Field("功能", description="功能|接口|Web页面|Agent测试")
    web_page_url: Optional[str] = Field(None, description="Web测试时的页面URL")
    web_locator_hint: Optional[str] = Field(None, description="Web测试时的元素定位提示")


class GenerateCasesFromPointsRequest(BaseModel):
    project_id: UUID
    test_point_ids: List[UUID]
    agent_id: Optional[UUID] = None
    document_ids: Optional[List[UUID]] = None
    version_id: Optional[UUID] = None


class VerifyCasesRequest(BaseModel):
    project_id: UUID
    case_ids: List[UUID]
    agent_id: Optional[UUID] = None
