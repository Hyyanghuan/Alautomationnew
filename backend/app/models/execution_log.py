import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    DEBUG = "debug"


class TriggerType(str, enum.Enum):
    MANUAL = "manual"
    CI = "ci"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"


class TestExecutionLog(Base):
    __tablename__ = "test_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_executions.id", ondelete="CASCADE"), index=True
    )
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_execution_results.id", ondelete="SET NULL"), nullable=True
    )
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel), default=LogLevel.INFO)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
