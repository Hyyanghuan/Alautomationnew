from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validation import (
    strip_optional_str,
    strip_required_str,
    validate_optional_url,
    validate_test_point_type_field,
    validate_uuid_list,
    VALID_LOCATOR_STRATEGIES,
)


class ElementLocator(BaseModel):
    strategy: str = Field("css", description="css|xpath|id|text|role")
    value: str = Field("", max_length=500)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        key = (v or "css").strip().lower()
        if key not in VALID_LOCATOR_STRATEGIES:
            allowed = ", ".join(sorted(VALID_LOCATOR_STRATEGIES))
            raise ValueError(f"定位策略无效，允许值: {allowed}")
        return key

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        return (v or "").strip()[:500]


class TestPointNode(BaseModel):
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[UUID] = None
    feature_id: Optional[UUID] = None
    sort_order: int = Field(0, ge=0, le=9999)
    test_type: Optional[str] = Field(None, description="功能|接口|Web页面|Agent测试")
    locator: Optional[ElementLocator] = None
    children: List["TestPointNode"] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return strip_required_str(v, field_name="测试点名称", max_len=255)

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        return validate_test_point_type_field(v)


TestPointNode.model_rebuild()


class TestPointTreeSave(BaseModel):
    project_id: UUID
    tree: List[TestPointNode] = Field(..., min_length=0, max_length=500)
    remark: Optional[str] = Field(None, max_length=2000)

    @field_validator("remark")
    @classmethod
    def validate_remark(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=2000)


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
    document_ids: Optional[List[UUID]] = Field(None, description="关联需求文档ID")
    kb_ids: Optional[List[UUID]] = Field(None, description="引用知识库ID")
    feature_ids: Optional[List[UUID]] = None
    requirements_text: Optional[str] = Field(None, max_length=50_000)
    test_point_type: str = Field("功能", description="功能|接口|Web页面|Agent测试")
    web_page_url: Optional[str] = Field(None, description="Web测试时的页面URL")
    web_locator_hint: Optional[str] = Field(None, max_length=2000)

    @field_validator("test_point_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        return validate_test_point_type_field(v)

    @field_validator("requirements_text")
    @classmethod
    def validate_requirements_text(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=50_000)

    @field_validator("web_locator_hint")
    @classmethod
    def validate_locator_hint(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=2000)

    @field_validator("document_ids", "kb_ids", "feature_ids")
    @classmethod
    def validate_id_lists(cls, v: Optional[List[UUID]]) -> Optional[List[UUID]]:
        if v is None:
            return None
        return validate_uuid_list(v, field_name="ID列表", min_items=0, max_items=100)

    @field_validator("web_page_url")
    @classmethod
    def validate_web_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_url(v, field_name="web_page_url")

    @model_validator(mode="after")
    def validate_web_type(self):
        if self.test_point_type == "Web页面" and not self.web_page_url:
            raise ValueError("Web页面测试须填写 web_page_url")
        return self


class GenerateCasesFromPointsRequest(BaseModel):
    project_id: UUID
    test_point_ids: List[UUID] = Field(..., min_length=1, max_length=200)
    agent_id: Optional[UUID] = None
    document_ids: Optional[List[UUID]] = None
    version_id: Optional[UUID] = None

    @field_validator("test_point_ids")
    @classmethod
    def validate_point_ids(cls, v: List[UUID]) -> List[UUID]:
        return validate_uuid_list(v, field_name="test_point_ids", min_items=1, max_items=200)

    @field_validator("document_ids")
    @classmethod
    def validate_doc_ids(cls, v: Optional[List[UUID]]) -> Optional[List[UUID]]:
        if v is None:
            return None
        return validate_uuid_list(v, field_name="document_ids", min_items=0, max_items=50)


class VerifyCasesRequest(BaseModel):
    project_id: UUID
    case_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    agent_id: Optional[UUID] = None

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, v: List[UUID]) -> List[UUID]:
        return validate_uuid_list(v, field_name="case_ids", min_items=1, max_items=100)
