from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.validation import strip_optional_str, strip_required_str, validate_steps_field, validate_uuid_list
from app.models.test_case import CasePriority, CaseStatus


class TestCaseCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    version_id: Optional[UUID] = None
    test_point_id: Optional[UUID] = None
    precondition: Optional[str] = Field(None, max_length=5000)
    steps: Optional[list] = None
    expected_result: Optional[str] = Field(None, max_length=5000)
    priority: CasePriority = CasePriority.P2
    status: CaseStatus = CaseStatus.ENABLED
    tags: Optional[list] = None
    type_ids: Optional[List[UUID]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return strip_required_str(v, field_name="用例名称", max_len=255)

    @field_validator("precondition", "expected_result")
    @classmethod
    def validate_text(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=5000)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: Optional[list], info):
        return validate_steps_field(v, info)

    @field_validator("type_ids")
    @classmethod
    def validate_type_ids(cls, v: Optional[List[UUID]]) -> Optional[List[UUID]]:
        if v is None:
            return None
        return validate_uuid_list(v, field_name="type_ids", min_items=0, max_items=20)


class TestCaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    precondition: Optional[str] = Field(None, max_length=5000)
    steps: Optional[list] = None
    expected_result: Optional[str] = Field(None, max_length=5000)
    priority: Optional[CasePriority] = None
    status: Optional[CaseStatus] = None
    tags: Optional[list] = None
    type_ids: Optional[List[UUID]] = None
    script_content: Optional[str] = Field(None, max_length=100_000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return strip_required_str(v, field_name="用例名称", max_len=255)

    @field_validator("precondition", "expected_result")
    @classmethod
    def validate_text(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=5000)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: Optional[list], info):
        return validate_steps_field(v, info)

    @field_validator("type_ids")
    @classmethod
    def validate_type_ids(cls, v: Optional[List[UUID]]) -> Optional[List[UUID]]:
        if v is None:
            return None
        return validate_uuid_list(v, field_name="type_ids", min_items=0, max_items=20)


class TestCaseOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    precondition: Optional[str]
    steps: Optional[list]
    expected_result: Optional[str]
    priority: CasePriority
    status: CaseStatus = CaseStatus.ENABLED
    tags: Optional[list]
    test_point_id: Optional[UUID]
    version_id: Optional[UUID]
    script_content: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    type_names: List[str] = []
    type_ids: List[UUID] = []

    model_config = {"from_attributes": True}


class TestCaseTypeOut(BaseModel):
    id: UUID
    name: str
    color: str
    description: Optional[str] = None
    is_preset: bool = True

    model_config = {"from_attributes": True}


class BatchLinkPlanRequest(BaseModel):
    case_ids: List[UUID] = Field(..., min_length=1, max_length=500)
    plan_id: UUID

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, v: List[UUID]) -> List[UUID]:
        return validate_uuid_list(v, field_name="case_ids", min_items=1, max_items=500)


class BatchLinkTypeRequest(BaseModel):
    case_ids: List[UUID] = Field(..., min_length=1, max_length=500)
    type_ids: List[UUID] = Field(..., min_length=1, max_length=20)

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, v: List[UUID]) -> List[UUID]:
        return validate_uuid_list(v, field_name="case_ids", min_items=1, max_items=500)

    @field_validator("type_ids")
    @classmethod
    def validate_type_ids(cls, v: List[UUID]) -> List[UUID]:
        return validate_uuid_list(v, field_name="type_ids", min_items=1, max_items=20)
