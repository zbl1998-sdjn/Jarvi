import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_message_sequence: Mapped[int] = mapped_column(Integer, default=0)
    next_realtime_event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.sequence",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("session_id", "sequence", name="uq_chat_messages_session_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    session: Mapped[ChatSession] = relationship(back_populates="messages")


class RealtimeEvent(Base):
    __tablename__ = "realtime_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence",
            name="uq_realtime_events_session_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class ActionAudit(Base):
    __tablename__ = "action_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(32))
    target: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_type: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(String(128), default="")
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    last_confirmed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class UserProfileFact(Base):
    __tablename__ = "user_profile_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_type: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    last_confirmed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class SessionArtifact(Base):
    __tablename__ = "session_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, default="")


class PreferenceState(Base):
    __tablename__ = "preference_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_style: Mapped[str] = mapped_column(String(64), default="幽默风趣型")
    voice_name: Mapped[str] = mapped_column(String(128), default="zh-CN-XiaoxiaoNeural")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )


class WorkspaceState(Base):
    __tablename__ = "workspace_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    active_workspace: Mapped[str] = mapped_column(String(32), default="console")
    last_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )


class UploadedContext(Base):
    __tablename__ = "uploaded_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )


class TaskItem(Base):
    __tablename__ = "task_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    stage: Mapped[str] = mapped_column(String(16), default="M6")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )


class ReminderEvent(Base):
    __tablename__ = "reminder_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message: Mapped[str] = mapped_column(Text)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("task_items.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
    )
