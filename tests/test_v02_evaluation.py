"""Infrastructure tests plus explicit expected failures for frozen known safety gaps."""
import copy,hashlib,json
from pathlib import Path
import pytest
from app.core.config import Settings
from app.services.risk import RiskEngine,FamilyContext,RISK_TYPES,WEIGHTS
from evaluation.v02.benchmark import confusion,metrics,keyword,predict,paired_interval
from evaluation.v02.review import reconcile,export_packets
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'evaluation/v02';CASES=json.loads((D/'cases.json').read_text());GAPS=json.loads((D/'known-gaps.json').read_text())['cases']

def test_v01_source_is_unchanged():
 for path,expected in json.loads((D/'baseline/v01-sha256.json').read_text()).items():
  assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path

def test_dataset_manifest_and_schema():
 manifest=json.loads((D/'manifest.json').read_text())
 assert hashlib.sha256((D/'cases.json').read_bytes()).hexdigest()==manifest['sha256']
 assert len(CASES)==260
 assert len({r['id'] for r in CASES})==len(CASES)
 assert len({r['message'] for r in CASES})==len(CASES)
 assert set('ABCDEFGHIJKLMNOPQR')=={b for r in CASES for b in r['buckets']}
 for c in CASES:
  assert c['dataset_version']==manifest['version'] and c['source_type']=='SYNTHETIC'
  assert c['expected_category'] in RISK_TYPES and set(c['expected_signals'])<=set(WEIGHTS)
  assert c['reviewer_1'] is c['reviewer_2'] is c['final_label'] is c['agreement'] is None
  if c['expected_risk_level']=='AMBIGUOUS':assert c['caregiver_escalation_expected'] is None
  else:assert c['caregiver_escalation_expected']==(c['expected_risk_level'] in ('HIGH','CRITICAL'))

def test_metric_hand_calculation():
 m=confusion([True,True,False,False],[True,False,True,False])
 assert (m['TP'],m['TN'],m['FP'],m['FN'])==(1,1,1,1)
 assert m['precision']==m['recall']==m['F1']==m['false_positive_rate']==.5

def test_zero_denominators_not_fake_perfection():
 m=confusion([],[])
 assert m['precision'] is m['recall'] is m['F1'] is m['false_positive_rate'] is None

def test_ambiguous_excluded():
 out,_=predict([next(c for c in CASES if c['expected_risk_level']=='AMBIGUOUS')])
 m=metrics(out['B_yatharth']);assert m['n']==0 and m['excluded_ambiguous']==1

def test_human_mode_does_not_use_proposals():
 out,ai=predict(CASES,mode='human')
 assert all(not rows for rows in out.values());assert ai['status']=='NOT_RUN'

def test_no_live_ai_claim_without_provider():
 out,status=predict(CASES[:1])
 assert 'C_yatharth_AI' not in out and status['status']=='NOT_RUN'

def test_keywords_are_evaluation_only():
 assert keyword('Never share your OTP')['severity']=='HIGH'
 assert keyword('अपना ओटीपी भेजें',True)['severity']=='HIGH'
 assert 'keyword' not in (ROOT/'app/main.py').read_text()

def annotation(case,reviewer,level='LOW'):
 return dict(id=case['id'],dataset_version=case['dataset_version'],message=case['message'],reviewer_id=reviewer,reviewed_at='2026-10-05T00:00:00Z',is_human=True,risk_level=level,category='NONE',signals=[],escalate=level in ('HIGH','CRITICAL'))

def test_review_disagreement_is_ambiguous():
 c=CASES[0];rows,stats=reconcile([c],[annotation(c,'test-reviewer-A')],[annotation(c,'test-reviewer-B','HIGH')])
 assert rows[0]['final_label']['risk_level']=='AMBIGUOUS' and rows[0]['final_label']['escalate'] is None
 assert stats['risk_level_agreement']==0

def test_same_reviewer_rejected():
 c=CASES[0]
 with pytest.raises(ValueError):reconcile([c],[annotation(c,'same')],[annotation(c,'same')])

def test_unknown_duplicate_and_mismatched_reviews_rejected():
 c=CASES[0];r=annotation(c,'r1')
 with pytest.raises(ValueError):reconcile([c],[r,r],[])
 changed={**r,'message':'changed'}
 with pytest.raises(ValueError):reconcile([c],[changed],[])

def test_unreviewed_labels_stay_null_and_packets_blind(tmp_path):
 rows,stats=reconcile(CASES,[],[])
 assert stats['completed_pairs']==0 and stats['risk_level_cohen_kappa'] is None
 export_packets(CASES,tmp_path)
 text=(tmp_path/'reviewer_1.jsonl').read_text()
 assert 'prediction' not in text and 'expected_risk_level' not in text
 assert len(text.splitlines())==260

def test_complete_review_agreement():
 c=CASES[0];rows,stats=reconcile([c],[annotation(c,'A')],[annotation(c,'B')])
 assert rows[0]['label_status']=='HUMAN_AGREED' and stats['full_label_agreement']==1
 assert stats['risk_level_cohen_kappa'] is None # single constant class

def test_paired_interval_reproducible():
 out,_=predict(CASES[:9]);assert paired_interval(out['A_keyword'],out['B_yatharth'],20)==paired_interval(out['A_keyword'],out['B_yatharth'],20)

PARAMS=[]
for case in CASES:
 marks=[]
 if case['caregiver_escalation_expected'] is None:marks=[pytest.mark.skip(reason='Ambiguous; no binary ground truth')]
 elif case['id'] in GAPS:marks=[pytest.mark.xfail(strict=True,reason='Known provisional-label gap: '+GAPS[case['id']]['reason'])]
 PARAMS.append(pytest.param(case,id=case['id'],marks=marks))
@pytest.mark.parametrize('case',PARAMS)
def test_v02_proposed_escalation_regression(case):
 result=RiskEngine(Settings(llm_enabled=False,openworker_enabled=False,high_threshold=60,critical_threshold=80)).analyze(case['message'],FamilyContext())
 assert (result['severity'] in ('HIGH','CRITICAL'))==case['caregiver_escalation_expected']
