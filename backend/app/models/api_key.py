import uuid
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which provider this key routes to (null = use settings default)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    
    # List of allowed models. Empty list means no restriction.
    allowed_models: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    token_limit_daily: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")  # noqa: F821
    provider = relationship("Provider", back_populates="api_keys", foreign_keys=[provider_id])
    usage_logs: Mapped[list["UsageLog"]] = relationship(  # noqa: F821
        "UsageLog", back_populates="api_key"
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}... ({self.status}) provider={self.provider_id}>"
