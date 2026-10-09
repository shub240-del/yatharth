"""Erase expired raw content; retain minimal derived decisions/audit for prototype review."""
from datetime import timedelta
from sqlalchemy import select
from app.models import Message, AuditLog, now
from app.core.config import Settings
from app.core.database import database

def purge(db, days):
    rows = list(db.scalars(select(Message).where(Message.created_at < now()-timedelta(days=days), Message.content.is_not(None))))
    for row in rows:
        row.content = None
        # Remove even the unsalted text digest; idempotent replay no longer applies.
        row.content_digest = ''
        db.add(AuditLog(actor='system', action='RAW_CONTENT_EXPIRED', resource=row.id, family_id=row.family_id))
    return len(rows)

if __name__ == '__main__':
    settings = Settings(); engine, sessions = database(settings.database_url)
    with sessions.begin() as db: print({'raw_messages_erased':purge(db, settings.retention_days)})
