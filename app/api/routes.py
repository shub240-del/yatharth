import hashlib
import hmac
import secrets
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from app.models import User, Family, FamilyMember, Consent, Message, Event, RiskEvent, Alert, AuditLog, Notification, now
from app.schemas import UserCreate, Login, FamilyCreate, MemberCreate, ConsentCreate, MessageInput, Feedback
from app.core.security import hasher, verify, token, DUMMY_HASH
from app.services.context import build_context

router = APIRouter(prefix='/api/v1')
bearer = HTTPBearer(auto_error=False)

def get_db(request: Request):
    # SQLite development uses one process-wide lock for grant/analyze/revoke ordering.
    # PostgreSQL uses person row locks and can run multiple workers.
    with request.app.state.db_lock:
        with request.app.state.sessions.begin() as db:
            yield db

DB = Depends(get_db, scope='function')

def actor(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer), db=DB):
    try:
        if not credentials: raise ValueError()
        data = jwt.decode(credentials.credentials, request.app.state.settings.jwt_secret, algorithms=['HS256'], issuer='yatharth', audience='yatharth-api', options={'require':['sub','exp','iat']})
        user = db.get(User, data['sub'])
        if not user: raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Valid authentication required', headers={'WWW-Authenticate':'Bearer'})

AUTH = Depends(actor)

def get_or_404(db, cls, id):
    item = db.get(cls, id)
    if item is None: raise HTTPException(404, 'Resource not found')
    return item

def member(db, family_id, user):
    family = get_or_404(db, Family, family_id)
    row = db.scalar(select(FamilyMember).where(FamilyMember.family_id == family_id, FamilyMember.user_id == user.id))
    if not row: raise HTTPException(403, 'Family membership required')
    return family

def audit(db, actor_id, action, resource, family_id=None):
    db.add(AuditLog(actor=actor_id, action=action, resource=resource, family_id=family_id))

def public(item, exclude=()):
    return {column.name:getattr(item,column.name) for column in item.__table__.columns if column.name not in exclude}

def user_view(user):
    return public(user, ('password_hash',))

def lock_person(db, id):
    return db.scalar(select(User).where(User.id == id).with_for_update())

def consent_for(db, family_id, person_id):
    return db.scalar(select(Consent).where(Consent.family_id == family_id, Consent.protected_person_id == person_id, Consent.scope == 'DIGITAL_SAFETY'))

def permitted_alert(db, id, user):
    alert = get_or_404(db, Alert, id)
    if user.role != 'CAREGIVER' or alert.caregiver_id != user.id: raise HTTPException(403, 'Alert is assigned to another caregiver')
    member(db, alert.family_id, user)
    return alert

def alert_view(db, alert):
    risk = db.get(RiskEvent, alert.risk_event_id)
    return {**public(alert), 'risk_type':risk.risk_type, 'risk_score':risk.risk_score, 'signals':risk.signals, 'recommended_action':risk.recommended_action}

@router.get('/health')
def health(request: Request, db=DB):
    db.execute(select(1))
    return {'status':'ok', 'service':'yatharth', 'rules':'rules-0.1', 'llm_enabled':request.app.state.settings.llm_enabled, 'openworker_enabled':request.app.state.settings.openworker_enabled}

@router.post('/users', status_code=201)
def create_user(body: UserCreate, db=DB):
    if db.scalar(select(User).where(User.email == body.email)): raise HTTPException(409, 'Account cannot be created with these details')
    user = User(**body.model_dump(exclude={'password'}), password_hash=hasher.hash(body.password))
    db.add(user); db.flush()
    audit(db, user.id, 'USER_CREATED', user.id)
    return user_view(user)

@router.post('/auth/login')
def login(body: Login, request: Request, db=DB):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not verify(body.password, user.password_hash if user else DUMMY_HASH) or not user: raise HTTPException(401, 'Invalid credentials')
    audit(db, user.id, 'LOGIN', user.id)
    return {'access_token':token(user.id, request.app.state.settings), 'token_type':'bearer', 'user':user_view(user)}

@router.get('/users/{id}')
def get_user(id: str, user=AUTH):
    if id != user.id: raise HTTPException(403, 'Only your own account is accessible')
    return user_view(user)

@router.post('/families', status_code=201)
def create_family(body: FamilyCreate, user=AUTH, db=DB):
    code = secrets.token_urlsafe(24)
    family = Family(name=body.name, owner_id=user.id, join_digest=hashlib.sha256(code.encode()).hexdigest())
    db.add(family); db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=user.id, relationship='Creator'))
    audit(db, user.id, 'FAMILY_CREATED', family.id, family.id)
    return {**public(family, ('join_digest',)), 'join_code':code}

@router.get('/families')
def list_families(user=AUTH, db=DB):
    return [public(f, ('join_digest',)) for f in db.scalars(select(Family).join(FamilyMember).where(FamilyMember.user_id == user.id))]

@router.get('/families/{id}')
def get_family(id: str, user=AUTH, db=DB):
    family = member(db, id, user)
    rows = db.execute(select(FamilyMember, User).join(User, User.id == FamilyMember.user_id).where(FamilyMember.family_id == id)).all()
    return {**public(family, ('join_digest',)), 'members':[{'user_id':u.id,'name':u.name,'role':u.role,'relationship':m.relationship} for m,u in rows]}

@router.post('/families/{id}/members', status_code=201)
def add_member(id: str, body: MemberCreate, user=AUTH, db=DB):
    family = get_or_404(db, Family, id)
    if body.user_id != user.id: raise HTTPException(403, 'Members must join using their own account')
    if family.owner_id != user.id and not hmac.compare_digest(family.join_digest, hashlib.sha256(body.join_code.encode()).hexdigest()): raise HTTPException(403, 'Valid family invitation required')
    existing = db.scalar(select(FamilyMember).where(FamilyMember.family_id == id, FamilyMember.user_id == user.id))
    if existing:
        existing.relationship = body.relationship
        return public(existing)
    # Lock the family to order membership vs. consent decisions.
    db.scalar(select(Family).where(Family.id == id).with_for_update())
    # New caregivers change the sharing audience: invalidate existing grants.
    if user.role == 'CAREGIVER':
        for consent in db.scalars(select(Consent).where(Consent.family_id == id, Consent.status == 'GRANTED')):
            lock_person(db, consent.protected_person_id)
            consent.status, consent.revoked_at = 'REVOKED', now()
            audit(db, user.id, 'CONSENT_AUDIENCE_CHANGED', consent.id, id)
    row = FamilyMember(family_id=id, user_id=user.id, relationship=body.relationship)
    db.add(row); db.flush()
    audit(db, user.id, 'MEMBER_JOINED', row.id, id)
    return public(row)

@router.post('/consents', status_code=201)
def grant_consent(body: ConsentCreate, user=AUTH, db=DB):
    member(db, body.family_id, user)
    if user.role != 'PROTECTED_PERSON' or user.id != body.protected_person_id: raise HTTPException(403, 'Only the protected person can grant their consent')
    db.scalar(select(Family).where(Family.id == body.family_id).with_for_update())
    lock_person(db, user.id)
    consent = consent_for(db, body.family_id, user.id)
    if not consent:
        consent = Consent(**body.model_dump(), status='GRANTED'); db.add(consent)
    else:
        consent.status, consent.granted_at, consent.revoked_at = 'GRANTED', now(), None
        consent.external_ai_allowed = body.external_ai_allowed
    db.flush()
    audit(db, user.id, 'CONSENT_GRANTED', consent.id, body.family_id)
    return public(consent)

@router.get('/consents')
def list_consents(family_id: str, user=AUTH, db=DB):
    member(db, family_id, user)
    query = select(Consent).where(Consent.family_id == family_id)
    if user.role == 'PROTECTED_PERSON': query = query.where(Consent.protected_person_id == user.id)
    return [public(c) for c in db.scalars(query)]

@router.post('/consents/{id}/revoke')
def revoke_consent(id: str, user=AUTH, db=DB):
    c = get_or_404(db, Consent, id)
    if c.protected_person_id != user.id: raise HTTPException(403, 'Only the protected person can revoke consent')
    db.scalar(select(Family).where(Family.id == c.family_id).with_for_update())
    lock_person(db, user.id)
    db.refresh(c)
    c.status, c.revoked_at = 'REVOKED', now()
    audit(db, user.id, 'CONSENT_REVOKED', c.id, c.family_id)
    return public(c)

def analysis_view(db, message, risk):
    alerts = list(db.scalars(select(Alert).where(Alert.risk_event_id == risk.id)))
    return {**public(risk), 'risk_event_id':risk.id, 'message_id':message.id, 'alert_created':bool(alerts), 'alert_id':alerts[0].id if alerts else None, 'alert_ids':[a.id for a in alerts], 'response_status':'ALERT_CREATED' if alerts else ('NO_CAREGIVER_CONFIGURED' if risk.severity in ('HIGH','CRITICAL') else 'NO_ALERT_REQUIRED')}

@router.post('/messages/analyze')
def analyze(body: MessageInput, request: Request, user=AUTH, db=DB):
    member(db, body.family_id, user)
    sender = get_or_404(db, User, body.sender_id)
    if sender.id != user.id or user.role != 'PROTECTED_PERSON': raise HTTPException(403, 'Submit signals from your own protected-person account')
    db.scalar(select(Family).where(Family.id == body.family_id).with_for_update())
    lock_person(db, user.id)
    consent = consent_for(db, body.family_id, user.id)
    if not consent or consent.status != 'GRANTED': raise HTTPException(403, 'Active DIGITAL_SAFETY consent required')
    digest = hashlib.sha256(body.content.encode()).hexdigest()
    if body.request_id:
        old = db.scalar(select(Message).where(Message.sender_id == user.id, Message.request_id == body.request_id))
        if old:
            if old.content_digest != digest or old.family_id != body.family_id or old.source != body.source: raise HTTPException(409, 'Request ID already used with different input')
            return analysis_view(db, old, db.scalar(select(RiskEvent).where(RiskEvent.message_id == old.id)))
    context, caregivers = build_context(db, body.family_id, user.id, consent.id)
    decision = request.app.state.risk_engine.analyze(body.content, context, external_allowed=consent.external_ai_allowed)
    message = Message(**body.model_dump(), content_digest=digest)
    db.add(message); db.flush()
    db.add(Event(family_id=body.family_id, person_id=user.id, event_type='MESSAGE_RECEIVED', source=body.source, payload={'message_id':message.id, 'consent_id':consent.id}))
    risk = RiskEvent(family_id=body.family_id, message_id=message.id, **decision)
    db.add(risk); db.flush()
    audit(db, user.id, 'MESSAGE_ANALYZED', message.id, body.family_id)
    audit(db, user.id, 'RISK_CREATED', risk.id, body.family_id)
    if risk.severity in ('HIGH','CRITICAL'):
        for caregiver in caregivers:
            alert = Alert(family_id=body.family_id, risk_event_id=risk.id, caregiver_id=caregiver.id, severity=risk.severity, title='Potential scam indicators detected', summary=risk.explanation)
            db.add(alert); db.flush()
            db.add(Notification(alert_id=alert.id))
            audit(db, user.id, 'ALERT_CREATED', alert.id, body.family_id)
    db.flush()
    return analysis_view(db, message, risk)

@router.get('/messages/{id}')
def get_message(id: str, user=AUTH, db=DB):
    message = get_or_404(db, Message, id)
    if message.sender_id != user.id: raise HTTPException(403, 'Raw messages are restricted to the protected person in V1')
    audit(db, user.id, 'MESSAGE_VIEWED', id, message.family_id)
    return public(message, ('content_digest',))

@router.get('/risk-events/{id}')
def get_risk(id: str, user=AUTH, db=DB):
    risk = get_or_404(db, RiskEvent, id)
    message = db.get(Message, risk.message_id)
    if message.sender_id != user.id:
        if not db.scalar(select(Alert).where(Alert.risk_event_id == id, Alert.caregiver_id == user.id)): raise HTTPException(403, 'Risk summary is not assigned to you')
    member(db, risk.family_id, user)
    audit(db, user.id, 'RISK_VIEWED', id, risk.family_id)
    return public(risk)

@router.get('/alerts')
def list_alerts(user=AUTH, db=DB, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    if user.role != 'CAREGIVER': raise HTTPException(403, 'Caregiver role required')
    alerts = list(db.scalars(select(Alert).where(Alert.caregiver_id == user.id).order_by(Alert.created_at.desc()).limit(limit).offset(offset)))
    for item in alerts: audit(db, user.id, 'ALERT_VIEWED', item.id, item.family_id)
    return [alert_view(db, a) for a in alerts]

@router.get('/alerts/{id}')
def get_alert(id: str, user=AUTH, db=DB):
    alert = permitted_alert(db, id, user)
    audit(db, user.id, 'ALERT_VIEWED', id, alert.family_id)
    return alert_view(db, alert)

@router.post('/alerts/{id}/acknowledge')
def acknowledge(id: str, user=AUTH, db=DB):
    alert = permitted_alert(db, id, user)
    db.refresh(alert, with_for_update=True)
    if alert.status == 'RESOLVED': raise HTTPException(409, 'Resolved alerts cannot be reopened')
    if alert.status == 'UNREAD':
        alert.status, alert.acknowledged_at = 'ACKNOWLEDGED', now()
        audit(db, user.id, 'ALERT_ACKNOWLEDGED', id, alert.family_id)
    return alert_view(db, alert)

@router.post('/alerts/{id}/resolve')
def resolve(id: str, user=AUTH, db=DB):
    alert = permitted_alert(db, id, user)
    db.refresh(alert, with_for_update=True)
    if alert.status == 'UNREAD': raise HTTPException(409, 'Acknowledge before resolving')
    if alert.status != 'RESOLVED':
        alert.status, alert.resolved_at = 'RESOLVED', now()
        audit(db, user.id, 'ALERT_RESOLVED', id, alert.family_id)
    return alert_view(db, alert)

@router.post('/alerts/{id}/feedback')
def feedback(id: str, body: Feedback, user=AUTH, db=DB):
    alert = permitted_alert(db, id, user)
    alert.feedback_label = body.label
    audit(db, user.id, 'FEEDBACK_RECORDED', id, alert.family_id)
    return alert_view(db, alert)

@router.get('/audit')
def get_audit(family_id: str, user=AUTH, db=DB, limit: int = Query(100, ge=1, le=200)):
    member(db, family_id, user)
    # Each account can inspect its own action trail. No family-wide surveillance feed.
    return [public(a) for a in db.scalars(select(AuditLog).where(AuditLog.family_id == family_id, AuditLog.actor == user.id).order_by(AuditLog.created_at.desc()).limit(limit))]
