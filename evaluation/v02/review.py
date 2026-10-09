"""Two-reviewer, prediction-blind annotation workflow. No automatic truth invention."""
import argparse,copy,json,random
from pathlib import Path
from app.services.risk import RISK_TYPES,WEIGHTS
ROOT=Path(__file__).parent
LEVELS={'LOW','MEDIUM','HIGH','CRITICAL','AMBIGUOUS'}

def export_packets(cases,out):
 out.mkdir(parents=True,exist_ok=True)
 for n in [1,2]:
  packet=[dict(id=c['id'],dataset_version=c['dataset_version'],message=c['message'],language=c['language'],reviewer_id=None,reviewed_at=None,is_human=False,risk_level=None,category=None,signals=None,escalate=None,notes='') for c in cases]
  random.Random(7200+n).shuffle(packet)
  (out/f'reviewer_{n}.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in packet)+'\n')

def validate_review(r,case):
 if r['dataset_version']!=case['dataset_version'] or r['message']!=case['message']:raise ValueError('Review input/version mismatch')
 if not r.get('reviewer_id') or not r.get('reviewed_at') or r.get('is_human') is not True:raise ValueError('Completed human identity, timestamp and attestation required')
 if r.get('risk_level') not in LEVELS or r.get('category') not in RISK_TYPES:raise ValueError('Invalid label')
 signals=r.get('signals')
 if not isinstance(signals,list) or any(s not in WEIGHTS for s in signals):raise ValueError('Invalid signals')
 want=None if r['risk_level']=='AMBIGUOUS' else r['risk_level'] in ('HIGH','CRITICAL')
 if r.get('escalate') is not want:raise ValueError('Escalation inconsistent with risk label')

def reconcile(cases,one,two):
 lookup={c['id']:c for c in cases}
 def index(records):
  result={}
  for r in records:
   if r['id'] not in lookup or r['id'] in result:raise ValueError('Unknown/duplicate review ID')
   validate_review(r,lookup[r['id']]);result[r['id']]=r
  return result
 a,b=index(one),index(two);rows=copy.deepcopy(cases);pairs=[]
 for c in rows:
  c['final_label']=None;c['agreement']=None;c['label_status']='UNREVIEWED'
  r1,r2=a.get(c['id']),b.get(c['id']);c['reviewer_1'],c['reviewer_2']=r1,r2
  if not(r1 and r2):continue
  if r1['reviewer_id']==r2['reviewer_id']:raise ValueError('Two different reviewers required')
  same=all(r1[k]==r2[k] for k in ['risk_level','category','escalate']) and set(r1['signals'])==set(r2['signals'])
  c['agreement']=same;c['label_status']='HUMAN_AGREED' if same else 'HUMAN_DISAGREEMENT'
  c['final_label']={k:r1[k] for k in ['risk_level','category','signals','escalate']} if same else dict(risk_level='AMBIGUOUS',category='UNKNOWN',signals=[],escalate=None)
  pairs.append((r1['risk_level'],r2['risk_level']))
 n=len(pairs);pa=sum(a==b for a,b in pairs)/n if n else None
 pe=sum((sum(a==level for a,b in pairs)/n)*(sum(b==level for a,b in pairs)/n) for level in LEVELS) if n else None
 stats={'completed_pairs':n,'total_cases':len(cases),'pair_coverage':n/len(cases) if cases else 0,'risk_level_agreement':pa,'full_label_agreement':sum(c['agreement'] is True for c in rows)/n if n else None,'risk_level_cohen_kappa':(pa-pe)/(1-pe) if pe is not None and pe<1 else None,'note':'Reviewer attestations are recorded; identity/human status must be verified by the study operator.'}
 return rows,stats

def read_jsonl(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['export','merge']);p.add_argument('--dataset',type=Path,default=ROOT/'cases.json');p.add_argument('--out',type=Path,required=True);p.add_argument('--reviewer-1',type=Path);p.add_argument('--reviewer-2',type=Path);a=p.parse_args();cases=json.loads(a.dataset.read_text())
 if a.action=='export':export_packets(cases,a.out)
 else:
  if not(a.reviewer_1 and a.reviewer_2):raise SystemExit('Two completed reviewer files required')
  data,stats=reconcile(cases,read_jsonl(a.reviewer_1),read_jsonl(a.reviewer_2));a.out.mkdir(parents=True,exist_ok=True)
  (a.out/'reviewed-cases.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(a.out/'agreement.json').write_text(json.dumps(stats,indent=2))
if __name__=='__main__':main()
