from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, JSON, Integer, Float, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class User(Record, Base):
    __tablename__ = 'users'
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(Text)

class Family(Record, Base):
    __tablename__ = 'families'
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    join_digest: Mapped[str] = mapped_column(String(64))

class FamilyMember(Record, Base):
    __tablename__ = 'family_members'
    __table_args__ = (UniqueConstraint('family_id', 'user_id'),)
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    relationship: Mapped[str] = mapped_column(String(60))

class Consent(Record, Base):
    __tablename__ = 'consents'
    __table_args__ = (UniqueConstraint('family_id', 'protected_person_id', 'scope'),)
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    protected_person_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    scope: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    external_ai_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Message(Record, Base):
    __tablename__ = 'messages'
    __table_args__ = (UniqueConstraint('sender_id', 'request_id'),)
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    content: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    request_id: Mapped[str | None] = mapped_column(String(100))
    content_digest: Mapped[str] = mapped_column(String(64))

class Event(Record, Base):
    __tablename__ = 'events'
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    event_type: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class RiskEvent(Record, Base):
    __tablename__ = 'risk_events'
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey('messages.id'), unique=True)
    risk_type: Mapped[str] = mapped_column(String(50))
    risk_score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    signals: Mapped[list] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(100))
    decision_trace: Mapped[dict] = mapped_column(JSON)

class Alert(Record, Base):
    __tablename__ = 'alerts'
    __table_args__ = (UniqueConstraint('risk_event_id', 'caregiver_id'),)
    family_id: Mapped[str] = mapped_column(ForeignKey('families.id'), index=True)
    risk_event_id: Mapped[str] = mapped_column(ForeignKey('risk_events.id'))
    caregiver_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='UNREAD')
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feedback_label: Mapped[str | None] = mapped_column(String(30))

class AuditLog(Record, Base):
    __tablename__ = 'audit_logs'
    family_id: Mapped[str | None] = mapped_column(ForeignKey('families.id'), index=True)
    actor: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[str] = mapped_column(String(100))

class Notification(Record, Base):
    __tablename__ = 'notifications'
    alert_id: Mapped[str] = mapped_column(ForeignKey('alerts.id'), unique=True)
    status: Mapped[str] = mapped_column(String(20), default='PENDING')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
