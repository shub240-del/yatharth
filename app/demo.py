"""Create an explicitly synthetic family and verify the loop through a running HTTP API."""
import argparse
import json
import secrets
from pathlib import Path
import httpx

SAFE='Beta, I reached the market.'
MEDIUM='I received a strange message from an unknown number.'
SCAM='I am from the police department. Your Aadhaar has been used in a crime. Do not tell your family. Transfer money immediately to avoid arrest.'

def run(base_url, synthetic_consent, report=None):
    if not synthetic_consent:
        raise SystemExit('Use --synthetic-consent only for the fictitious Gupta demo family. Real people must grant consent themselves.')
    client=httpx.Client(base_url=base_url.rstrip('/')+'/api/v1',timeout=10,trust_env=False)
    def call(method,path,body=None,token=None,expected=200):
        r=client.request(method,path,json=body,headers={'Authorization':'Bearer '+token} if token else {})
        assert r.status_code==expected, f'{method} {path}: {r.status_code}: {r.text}'
        return r.json()
    suffix=secrets.token_hex(4); password=secrets.token_urlsafe(20)
    def account(name,role):
        email=f'{name.split()[0].lower()}.{suffix}@example.test'
        u=call('POST','/users',dict(name=name,email=email,role=role,password=password),expected=201)
        t=call('POST','/auth/login',dict(email=email,password=password))['access_token']
        return u,t
    carer,ct=account('Amit Gupta','CAREGIVER')
    f=call('POST','/families',{'name':'Gupta Family — synthetic demo'},ct,201)
    parent,pt=account('Rajesh Gupta','PROTECTED_PERSON')
    call('POST',f"/families/{f['id']}/members",{'user_id':carer['id'],'relationship':'Son'},ct,201)
    call('POST',f"/families/{f['id']}/members",{'user_id':parent['id'],'relationship':'Father','join_code':f['join_code']},pt,201)
    body={'family_id':f['id'],'sender_id':parent['id'],'content':SAFE,'source':'SIMULATOR'}
    call('POST','/messages/analyze',body,pt,403)
    c=call('POST','/consents',{'family_id':f['id'],'protected_person_id':parent['id']},pt,201)
    results=[]
    for text,expected in [(SAFE,'LOW'),(MEDIUM,'MEDIUM'),(SCAM,'CRITICAL')]:
        r=call('POST','/messages/analyze',{**body,'content':text},pt)
        assert r['severity']==expected
        call('GET','/risk-events/'+r['risk_event_id'],token=pt)
        results.append({'severity':r['severity'],'score':r['risk_score'],'alert_created':r['alert_created']})
    alerts=call('GET','/alerts',token=ct)
    assert len(alerts)==1
    aid=alerts[0]['id']
    call('POST','/alerts/'+aid+'/acknowledge',{},ct)
    resolved=call('POST','/alerts/'+aid+'/resolve',{},ct)
    assert resolved['status']=='RESOLVED'
    assert SCAM not in json.dumps(alerts)
    call('GET','/messages/'+r['message_id'],token=ct,expected=403)
    call('POST','/consents/'+c['id']+'/revoke',{},pt)
    call('POST','/messages/analyze',body,pt,403)
    # Restore only the fictitious demonstration grant for the user's local walkthrough.
    call('POST','/consents',{'family_id':f['id'],'protected_person_id':parent['id']},pt,201)
    audit=call('GET','/audit?family_id='+f['id'],token=pt)
    health=call('GET','/health')
    summary={'result':'PASS','synthetic_only':True,'family_id':f['id'],'cases':results,'caregiver_status':resolved['status'],'audit_records_for_parent':len(audit),'revocation_blocked_analysis':True,'caregiver_raw_message_access':'DENIED','llm_enabled':health['llm_enabled'],'openworker_enabled':health['openworker_enabled']}
    if report: Path(report).write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print('Synthetic demo login accounts:', parent['email'], carer['email'])
    print('Generated demo password (both accounts):',password)
    client.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--base-url',default='http://127.0.0.1:8000'); p.add_argument('--synthetic-consent',action='store_true'); p.add_argument('--report')
    a=p.parse_args(); run(a.base_url,a.synthetic_consent,a.report)
