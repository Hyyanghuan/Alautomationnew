import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CasePriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CaseStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class TestCaseType(Base):
    __tablename__ = "test_case_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="#409EFF")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_preset: Mapped[bool] = mapped_column(default=True)


test_case_type_link = Table(
    "test_case_type_link",
    Base.metadata,
    Column("case_id", UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), primary_key=True),
    Column("type_id", UUID(as_uuid=True), ForeignKey("test_case_types.id", ondelete="CASCADE"), primary_key=True),
)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("project_versions.id"), nullable=True)
    test_point_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("test_points.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    precondition: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[CasePriority] = mapped_column(Enum(CasePriority), default=CasePriority.P2)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, values_callable=lambda x: [e.value for e in x]),
        default=CaseStatus.ENABLED,
        index=True,
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    script_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    types: Mapped[list["TestCaseType"]] = relationship(secondary=test_case_type_link, lazy="selectin")
