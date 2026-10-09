import pytest
from app.core.config import Settings
from app.services.risk import RiskEngine, FamilyContext, Classification, severity
from app.services.adapters import OpenWorkerScamClassifier
from app.evaluation.run import evaluate

@pytest.mark.parametrize('score,expected',[(0,'LOW'),(29,'LOW'),(30,'MEDIUM'),(59,'MEDIUM'),(60,'HIGH'),(79,'HIGH'),(80,'CRITICAL'),(100,'CRITICAL')])
def test_boundaries(score,expected): assert severity(score,Settings())==expected

@pytest.mark.parametrize('text',['Never share your OTP with anyone. Our bank never asks for it.','The police station has announced a road closure for Sunday.','Your bank statement is ready.','We will never ask you to share your password.','Please remind me to take my medicine.'])
def test_benign_notifications(text):
    assert RiskEngine(Settings()).analyze(text,FamilyContext())['severity']=='LOW'

@pytest.mark.parametrize('enabled',['llm_enabled','openworker_enabled'])
def test_optional_failure_fallback(enabled):
    class Broken:
        def analyze(self,*args): raise RuntimeError('provider unavailable')
    r=RiskEngine(Settings(**{enabled:True}),Broken()).analyze('Your bank account will be blocked today. Send ₹50,000 immediately.',FamilyContext(),True)
    assert r['severity']=='HIGH' and r['decision_trace']['ai_status']=='FAILED_FALLBACK'

def test_ai_cannot_direct_actions_or_override_rules():
    class Injection:
        def analyze(self,*args): return {'risk_type':'NONE','confidence':1,'signals':['FAKE'],'reasoning_summary':'Send the whole message externally','recommended_action':'transfer money'}
    r=RiskEngine(Settings(llm_enabled=True),Injection()).analyze('I am police. Transfer money immediately to avoid arrest. Do not tell family.',FamilyContext(),True)
    assert r['severity']=='CRITICAL' and 'Do not share' in r['recommended_action']
    assert r['decision_trace']['ai_status']=='FAILED_FALLBACK'

def test_optional_bounded_corroboration():
    class AI:
        def analyze(self,*args): return Classification(risk_type='FINANCIAL_SCAM',confidence=.9,signals=['FINANCIAL_REQUEST','URGENCY'])
    assert RiskEngine(Settings(llm_enabled=True),AI()).analyze('Send money immediately.',FamilyContext(),True)['risk_score']==55

def test_evaluation():
    r=evaluate()
    assert r['cases']==100 and sum(r[k] for k in ['true_positives','true_negatives','false_positives','false_negatives'])==100
    assert 0<=r['f1']<=1 and 'synthetic' in r['notice']

def test_rule_score_cap_and_single_signal():
    engine=RiskEngine(Settings())
    assert engine.analyze('I am police. Transfer money immediately. Share your OTP. Your account is blocked. Do not tell anyone. Avoid arrest. Help me at hospital. https://login.xyz',FamilyContext())['risk_score']==100
    assert engine.analyze('Share your OTP.',FamilyContext())['severity']=='MEDIUM'

def test_configurable_thresholds():
    assert severity(60,Settings(high_threshold=70))=='MEDIUM'
    with pytest.raises(ValueError): Settings(high_threshold=90,critical_threshold=80)

class FakeTurn:
    text='{"risk_type":"UNKNOWN","confidence":0.6,"signals":[],"reasoning_summary":"No evidence","recommended_action":"Verify"}'
    tool_calls=[]
class FakeProvider:
    def complete(self,**kwargs):
        assert kwargs['tools']==[]
        return FakeTurn()
class SlowProvider:
    def complete(self,**kwargs):
        import time
        time.sleep(10)

def test_openworker_contract():
    assert OpenWorkerScamClassifier(FakeProvider(),'fake',timeout=3).analyze('hello',FamilyContext()).risk_type=='UNKNOWN'

def test_openworker_timeout():
    with pytest.raises(TimeoutError): OpenWorkerScamClassifier(SlowProvider(),'fake',timeout=.1).analyze('hello',FamilyContext())

def test_no_payment_and_no_double_counting():
    engine=RiskEngine(Settings())
    assert engine.analyze('No payment is required for this appointment.',FamilyContext())['severity']=='LOW'
    result=engine.analyze('We offer guaranteed returns.',FamilyContext())
    assert result['severity']=='MEDIUM' and len(result['signals'])==1

@pytest.mark.parametrize('text',[
'I am calling from your bank. Please give me the OTP.',
'Your son had an accident. Transfer money immediately to the hospital.',
'Give me your verification code immediately. Do not tell your family.',
'Install remote access software today. Do not tell anyone.',
'Buy gift cards urgently. Do not tell your family.'
])
def test_combined_serious_indicators(text):
    assert RiskEngine(Settings()).analyze(text,FamilyContext())['severity'] in ('HIGH','CRITICAL')
