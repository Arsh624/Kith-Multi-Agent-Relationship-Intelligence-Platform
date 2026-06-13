import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("companies.id"), nullable=True
    )
    source_message_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("messages.id"), nullable=True
    )
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    favorite: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
