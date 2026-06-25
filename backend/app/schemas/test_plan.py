from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.validation import strip_optional_str, strip_required_str, validate_executor_type_field
from app.models.test_plan import ExecutionStrategy, PlanStatus


class PlanCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    version_id: Optional[UUID] = None
    strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    executor_type: str = Field("api", description="api|unit|e2e|performance|agent")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return strip_required_str(v, field_name="计划名称", max_len=255)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=2000)

    @field_validator("executor_type")
    @classmethod
    def validate_executor(cls, v: str) -> str:
        return validate_executor_type_field(v)


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    strategy: Optional[ExecutionStrategy] = None
    executor_type: Optional[str] = None
    status: Optional[PlanStatus] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return strip_required_str(v, field_name="计划名称", max_len=255)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        return strip_optional_str(v, max_len=2000)

    @field_validator("executor_type")
    @classmethod
    def validate_executor(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_executor_type_field(v)


class PlanOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    status: PlanStatus
    strategy: ExecutionStrategy
    executor_type: str
    executor_name: Optional[str] = None
    executor_tech: Optional[str] = None
    case_count: int = 0

    model_config = {"from_attributes": True}
