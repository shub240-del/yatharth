from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from app.models import Message, Event, RiskEvent, Alert, AuditLog, Notification, now
from app.api.routes import get_db
from app.services.notifications import deliver
from app.retention import purge

CRITICAL = 'I am from the police department. Your Aadhaar has been used in a crime. Do not tell your family. Transfer money immediately to avoid arrest.'

def submit(client,family,text=CRITICAL,**extra):
    return client.post('/api/v1/messages/analyze',headers=family['ph'],json={'family_id':family['f']['id'],'sender_id':family['parent']['id'],'content':text,**extra})

def test_health_and_auth(client):
    assert client.get('/api/v1/health').json()['status']=='ok'
    assert client.get('/api/v1/alerts').status_code==401
    assert client.get('/api/v1/alerts',headers={'Authorization':'Bearer nonsense'}).status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'nobody@example.test','password':'incorrect'}).status_code==401

def test_user_family_membership(client,family):
    assert client.get('/api/v1/users/'+family['parent']['id'],headers=family['ph']).status_code==200
    assert client.get('/api/v1/users/'+family['parent']['id'],headers=family['oh']).status_code==403
    r=client.get('/api/v1/families/'+family['f']['id'],headers=family['ph'])
    assert len(r.json()['members'])==2 and 'join_digest' not in r.text
    assert client.post('/api/v1/families/'+family['f']['id']+'/members',headers=family['oh'],json={'user_id':family['outsider']['id'],'relationship':'Spy'}).status_code==403

def test_no_consent_no_persistence(client,family,app):
    assert submit(client,family).status_code==403
    with app.state.sessions() as db:
        for cls in [Message,Event,RiskEvent,Alert]: assert db.scalar(select(func.count()).select_from(cls))==0

def test_consent_only_self_and_revocation(client,family,consent):
    assert client.post('/api/v1/consents',headers=family['ch'],json={'family_id':family['f']['id'],'protected_person_id':family['parent']['id']}).status_code==403
    assert client.post('/api/v1/consents/'+consent['id']+'/revoke',headers=family['ch']).status_code==403
    assert submit(client,family).status_code==200
    assert client.post('/api/v1/consents/'+consent['id']+'/revoke',headers=family['ph']).status_code==200
    assert submit(client,family).status_code==403

def test_full_loop_privacy_and_audit(client,family,consent,app):
    result=submit(client,family).json()
    assert result['severity']=='CRITICAL' and result['alert_created']
    aid=result['alert_id']; path='/api/v1/alerts/'+aid
    for suffix in ['', '/acknowledge','/resolve']:
        r=client.get(path,headers=family['oh']) if not suffix else client.post(path+suffix,headers=family['oh'])
        assert r.status_code==403
    assert client.get('/api/v1/messages/'+result['message_id'],headers=family['ch']).status_code==403
    assert client.get('/api/v1/messages/'+result['message_id'],headers=family['ph']).json()['content']==CRITICAL
    assert client.get('/api/v1/risk-events/'+result['risk_event_id'],headers=family['ch']).status_code==200
    assert client.get('/api/v1/risk-events/'+result['risk_event_id'],headers=family['oh']).status_code==403
    listed=client.get('/api/v1/alerts',headers=family['ch']).json()
    assert len(listed)==1 and CRITICAL not in str(listed)
    assert client.post(path+'/resolve',headers=family['ch']).status_code==409
    assert client.post(path+'/acknowledge',headers=family['ch']).json()['status']=='ACKNOWLEDGED'
    assert client.post(path+'/acknowledge',headers=family['ch']).status_code==200
    assert client.post(path+'/resolve',headers=family['ch']).json()['status']=='RESOLVED'
    assert client.post(path+'/resolve',headers=family['ch']).status_code==200
    assert client.post(path+'/acknowledge',headers=family['ch']).status_code==409
    assert client.post(path+'/feedback',headers=family['ch'],json={'label':'TRUE_RISK'}).json()['feedback_label']=='TRUE_RISK'
    with app.state.sessions() as db:
        actions={a.action for a in db.scalars(select(AuditLog))}
        assert {'CONSENT_GRANTED','MESSAGE_ANALYZED','RISK_CREATED','ALERT_CREATED','ALERT_VIEWED','ALERT_ACKNOWLEDGED','ALERT_RESOLVED'} <= actions
        assert CRITICAL not in str([a.resource for a in db.scalars(select(AuditLog))])
        assert db.scalar(select(func.count()).select_from(Event))==1

def test_safe_and_medium_no_alerts(client,family,consent):
    for text,severity in [('Beta, I reached the market.','LOW'),('I received a strange message from an unknown number.','MEDIUM')]:
        r=submit(client,family,text).json()
        assert r['severity']==severity and not r['alert_created']
        assert client.get('/api/v1/risk-events/'+r['risk_event_id'],headers=family['ch']).status_code==403

def test_high(client,family,consent):
    r=submit(client,family,'Your bank account will be blocked today. Send ₹50,000 immediately.').json()
    assert r['severity']=='HIGH' and r['alert_created']

def test_input_limits_and_missing_entities(client,family,consent):
    for text in ['', ' '*5, 'a'*10001]: assert submit(client,family,text).status_code==422
    assert submit(client,family,family_id='missing').status_code==404
    assert submit(client,family,sender_id='missing').status_code==404
    assert client.post('/api/v1/messages/analyze',headers=family['ch'],json={'family_id':family['f']['id'],'sender_id':family['parent']['id'],'content':CRITICAL}).status_code==403

def test_idempotency(client,family,consent,app):
    r1=submit(client,family,request_id='one').json(); r2=submit(client,family,request_id='one').json()
    assert r1['risk_event_id']==r2['risk_event_id']
    assert submit(client,family,'different',request_id='one').status_code==409
    with app.state.sessions() as db: assert db.scalar(select(func.count()).select_from(Alert))==1

def test_new_caregiver_requires_reconsent(client,family,consent):
    assert client.post('/api/v1/families/'+family['f']['id']+'/members',headers=family['oh'],json={'user_id':family['outsider']['id'],'relationship':'Uncle','join_code':family['f']['join_code']}).status_code==201
    assert submit(client,family).status_code==403
    assert client.post('/api/v1/consents',headers=family['ph'],json={'family_id':family['f']['id'],'protected_person_id':family['parent']['id']}).status_code==201
    assert len(submit(client,family).json()['alert_ids'])==2

def test_external_consent_blocks_provider(client,family,consent,app):
    class MustNotCall:
        def analyze(self,*args): raise AssertionError('Provider must not receive data')
    app.state.risk_engine.settings.llm_enabled=True; app.state.risk_engine.optional=MustNotCall()
    assert submit(client,family).json()['decision_trace']['ai_status']=='CONSENT_DISABLED'

def test_notification_failure_preserves_alert(client,family,consent,app):
    result=submit(client,family).json()
    class Broken:
        def notify(self,*args): raise RuntimeError('offline')
    deliver(app.state.sessions,Broken())
    with app.state.sessions() as db:
        assert db.get(Alert,result['alert_id'])
        assert db.scalar(select(Notification)).status=='FAILED'

def test_retention_erases_content(client,family,consent,app):
    r=submit(client,family).json()
    with app.state.sessions.begin() as db:
        db.get(Message,r['message_id']).created_at=now()-timedelta(days=40)
        assert purge(db,30)==1
    assert client.get('/api/v1/messages/'+r['message_id'],headers=family['ph']).json()['content'] is None

def test_database_failure_controlled(client,app):
    def fail(): raise OperationalError('query',{},Exception('private database details'))
    app.dependency_overrides[get_db]=fail
    r=client.get('/api/v1/health')
    assert r.status_code==503 and 'private database' not in r.text

def test_errors_do_not_echo_content(client,family):
    r=client.post('/api/v1/messages/analyze',headers=family['ph'],json={'family_id':family['f']['id'],'sender_id':family['parent']['id'],'content':'PRIVATE','password':'SECRET'})
    assert r.status_code==422 and 'SECRET' not in r.text and 'PRIVATE' not in r.text

def test_dashboard_and_openapi(client):
    assert client.get('/').status_code==200
    assert 'script-src' in client.get('/').headers['content-security-policy']
    assert client.get('/static/app.js').status_code==200
    assert '/api/v1/messages/analyze' in client.get('/openapi.json').json()['paths']

def test_transaction_rolls_back_on_persistence_failure(client,family,consent,app):
    original=app.state.risk_engine.analyze
    def invalid(*args,**kwargs):
        result=original(*args,**kwargs); result['risk_score']=None; return result
    app.state.risk_engine.analyze=invalid
    assert submit(client,family).status_code==409
    with app.state.sessions() as db:
        for cls in [Message,Event,RiskEvent,Alert]: assert db.scalar(select(func.count()).select_from(cls))==0

def test_concurrent_duplicate_is_single_event(client,family,consent,app):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    def one(_):
        return submit(TestClient(app),family,request_id='parallel')
    with ThreadPoolExecutor(2) as pool: rows=list(pool.map(one,range(2)))
    assert [r.status_code for r in rows]==[200,200]
    assert rows[0].json()['risk_event_id']==rows[1].json()['risk_event_id']
    with app.state.sessions() as db: assert db.scalar(select(func.count()).select_from(Alert))==1
