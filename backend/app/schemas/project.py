from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.project import ProjectStatus, VersionStatus

ProjectStatusAction = Literal["start", "pause", "suspend", "complete", "restart"]
VersionStatusAction = Literal["start", "suspend", "complete"]


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectStatusChange(BaseModel):
    action: ProjectStatusAction = Field(
        ...,
        description="start=启动 pause=暂停 suspend=挂起 complete=完成 restart=重启",
    )


class VersionStatusChange(BaseModel):
    action: VersionStatusAction = Field(..., description="start=启动 suspend=挂起 complete=完成")


class VersionUpdate(BaseModel):
    version_number: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    release_date: Optional[date] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: ProjectStatus
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VersionCreate(BaseModel):
    version_number: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    release_date: Optional[date] = None


class VersionOut(BaseModel):
    id: UUID
    project_id: UUID
    version_number: str
    description: Optional[str]
    status: VersionStatus
    start_date: Optional[date]
    release_date: Optional[date]
    created_at: datetime

    model_config = {"from_attributes": True}


class FeatureCreate(BaseModel):
    feature_name: str
    description: Optional[str] = None
    introduced_version: Optional[str] = None
    removed_version: Optional[str] = None


class FeatureUpdate(BaseModel):
    feature_name: Optional[str] = None
    description: Optional[str] = None
    introduced_version: Optional[str] = None
    removed_version: Optional[str] = None


class FeatureOut(BaseModel):
    id: UUID
    project_id: UUID
    feature_name: str
    description: Optional[str]
    introduced_version: Optional[str]
    removed_version: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FeatureTestPointNode(BaseModel):
    id: Optional[str] = None
    name: str
    children: List["FeatureTestPointNode"] = []


FeatureTestPointNode.model_rebuild()


class FeatureDetailOut(BaseModel):
    id: Optional[UUID] = None
    project_id: UUID
    feature_name: str
    description: Optional[str] = None
    introduced_version: Optional[str] = None
    removed_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    test_points: List[FeatureTestPointNode] = []
    root_point_id: Optional[str] = None
