from sqlalchemy import select, func
from app.models import RiskEvent, Message, FamilyMember, User
from app.services.risk import FamilyContext

def build_context(db, family_id, person_id, consent_id):
    caregivers = list(db.scalars(select(User).join(FamilyMember, FamilyMember.user_id == User.id).where(FamilyMember.family_id == family_id, User.role == 'CAREGIVER')))
    previous = db.scalar(select(func.count()).select_from(RiskEvent).join(Message).where(Message.family_id == family_id, Message.sender_id == person_id))
    return FamilyContext(family_id, person_id, len(caregivers), consent_id, previous), caregivers
