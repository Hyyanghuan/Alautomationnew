import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentType(str, enum.Enum):
    DESIGN = "design"
    CODE_ANALYSIS = "code_analysis"
    HEALING = "healing"
    DEFECT_PREDICTION = "defect_prediction"
    INTENT = "intent"


class AgentStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentInstance(Base):
    __tablename__ = "agent_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_model_configs.id"), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_templates.id"), nullable=True)
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.ENABLED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
