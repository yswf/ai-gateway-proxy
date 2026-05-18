import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class KeyApplication(Base):
    __tablename__ = "key_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Applicant
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which provider/source they want access to
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    # Application content
    requested_models: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    intended_use: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Workflow state: pending / approved / rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    # Review
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Auto-created API key on approval
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    provider = relationship("Provider", back_populates="applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    api_key = relationship("APIKey", foreign_keys=[api_key_id])

    def __repr__(self) -> str:
        return f"<KeyApplication user={self.user_id} provider={self.provider_id} status={self.status}>"
