from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.validation import validate_execution_environment


class RunPlanRequest(BaseModel):
    environment: Optional[dict] = Field(
        None,
        description="执行环境，如 base_url、target_url、headless",
    )

    @field_validator("environment")
    @classmethod
    def validate_env(cls, v: Optional[dict]) -> Optional[dict]:
        return validate_execution_environment(v)
