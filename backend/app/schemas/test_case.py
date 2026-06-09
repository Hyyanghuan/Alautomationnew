from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.test_case import CasePriority, CaseStatus


class TestCaseCreate(BaseModel):
    project_id: UUID
    name: str
    version_id: Optional[UUID] = None
    test_point_id: Optional[UUID] = None
    precondition: Optional[str] = None
    steps: Optional[list] = None
    expected_result: Optional[str] = None
    priority: CasePriority = CasePriority.P2
    status: CaseStatus = CaseStatus.ENABLED
    tags: Optional[list] = None
    type_ids: Optional[List[UUID]] = None


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    precondition: Optional[str] = None
    steps: Optional[list] = None
    expected_result: Optional[str] = None
    priority: Optional[CasePriority] = None
    status: Optional[CaseStatus] = None
    tags: Optional[list] = None
    type_ids: Optional[List[UUID]] = None
    script_content: Optional[str] = None


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
    case_ids: List[UUID]
    plan_id: UUID


class BatchLinkTypeRequest(BaseModel):
    case_ids: List[UUID]
    type_ids: List[UUID]
