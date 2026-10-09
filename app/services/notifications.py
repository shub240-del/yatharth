"""Persist-first notification boundary. V1 delivers alerts in-app only."""
from typing import Protocol
from sqlalchemy import select
from app.models import Notification, Alert

class NotificationProvider(Protocol):
    def notify(self, alert_id: str, caregiver_id: str) -> None: ...

class InAppNotificationProvider:
    def notify(self, alert_id, caregiver_id):
        return None  # durable alert is the in-app delivery

def deliver(session_factory, provider):
    with session_factory.begin() as db:
        rows = db.scalars(select(Notification).where(Notification.status != 'DELIVERED').with_for_update(skip_locked=True).limit(100))
        for item in rows:
            item.attempts += 1
            alert = db.get(Alert, item.alert_id)
            try:
                provider.notify(alert.id, alert.caregiver_id)
                item.status = 'DELIVERED'
            except Exception:
                item.status = 'FAILED'  # original alert remains; next pass retries
