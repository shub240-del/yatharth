"""Reproducible, offline evaluation. Never imported by the product API."""
import argparse,hashlib,json,math,os,random,re,statistics,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from app.core.config import Settings
from app.services.risk import RiskEngine,FamilyContext,PATTERNS
ROOT=Path(__file__).parent
EN=['otp','password','pin','cvv','transfer','gift card','crypto','arrest','kyc','guaranteed returns','remote access','urgent','immediately','http']
PARITY=EN+['ओटीपी','पासवर्ड','पिन','सीवीवी','पैसे','पैसा','गिरफ्तारी','केवाईसी','तुरंत','दूरस्थ','paise','paisa','turant','girftar','bhejo','गुप्त','ताबडतोब','अटक','सांगा']

def keyword(message,multilingual=False):
 text=unicodedata.normalize('NFKC',message).casefold()
 hits=[w for w in (PARITY if multilingual else EN) if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',text) or (w=='http' and 'http' in text)]
 score=80 if len(hits)>=3 else 60 if hits else 0
 return {'severity':'CRITICAL' if score==80 else 'HIGH' if score else 'LOW','risk_score':score,'risk_type':'UNKNOWN' if hits else 'NONE','signals':[], 'decision_trace':{'keywords':hits},'model_version':'keyword-parity-1.0' if multilingual else 'keyword-en-1.0'}

def ratio(a,b):return a/b if b else None

def confusion(truth,pred):
 tp=sum(a and b for a,b in zip(truth,pred));tn=sum(not a and not b for a,b in zip(truth,pred));fp=sum(not a and b for a,b in zip(truth,pred));fn=sum(a and not b for a,b in zip(truth,pred))
 return {'n':len(truth),'TP':tp,'TN':tn,'FP':fp,'FN':fn,'precision':ratio(tp,tp+fp),'recall':ratio(tp,tp+fn),'F1':ratio(2*tp,2*tp+fp+fn),'false_positive_rate':ratio(fp,fp+tn)}

def metrics(rows):
 valid=[r for r in rows if r['expected'] is not None]
 result=confusion([r['expected'] for r in valid],[r['predicted'] for r in valid])
 result['serious_risk_recall']=result['recall'];result['excluded_ambiguous']=len(rows)-len(valid)
 result['ambiguous_alert_rate']=ratio(sum(r['predicted'] for r in rows if r['expected'] is None),len(rows)-len(valid))
 result['exact_severity_accuracy']=ratio(sum(r['expected_level']==r['prediction']['severity'] for r in valid),len(valid))
 result['category_accuracy']=ratio(sum(r['expected_category']==r['prediction']['risk_type'] for r in valid),len(valid))
 for level in ['HIGH','CRITICAL']:
  truth=[r['expected_level']==level for r in valid];pred=[r['prediction']['severity']==level for r in valid]
  result[level]=confusion(truth,pred)
  selected=[r for r in valid if r['expected_level']==level]
  result[level]['alert_recall']=ratio(sum(r['predicted'] for r in selected),len(selected));result[level]['support']=len(selected)
 tp=sum(len(set(r['expected_signals'])&set(r['prediction']['signals'])) for r in valid)
 result['signal_precision']=ratio(tp,sum(len(set(r['prediction']['signals'])) for r in valid))
 result['signal_recall']=ratio(tp,sum(len(set(r['expected_signals'])) for r in valid))
 return result

def grouped(rows,key):
 groups=defaultdict(list)
 for row in rows:
  values=row[key] if isinstance(row[key],list) else [row[key]]
  for value in values:groups[value].append(row)
 return {key:metrics(value) for key,value in sorted(groups.items())}

def select_label(case,mode):
 if mode=='human':
  final=case.get('final_label')
  if not final:return None
  return final
 return {'risk_level':case['expected_risk_level'],'category':case['expected_category'],'signals':case['expected_signals'],'escalate':case['caregiver_escalation_expected']}

def predict(cases,mode='proposed',ai=False):
 engine=RiskEngine(Settings(llm_enabled=False,openworker_enabled=False,high_threshold=60,critical_threshold=80))
 models={'A_keyword':lambda c:keyword(c['message']),'A2_multilingual_keyword':lambda c:keyword(c['message'],True),'B_yatharth':lambda c:engine.analyze(c['message'],FamilyContext())}
 ai_meta={'status':'NOT_RUN','reason':'No live AI evaluation requested/configured; not equivalent to rules fallback.'}
 if ai:
  cfg=Settings(llm_enabled=True,openworker_enabled=False,high_threshold=60,critical_threshold=80)
  if not(cfg.llm_url and cfg.llm_key and cfg.llm_model):raise ValueError('AI requested but LLM_URL, LLM_API_KEY and LLM_MODEL are required')
  if any(c['source_type']!='SYNTHETIC' for c in cases):raise ValueError('This opt-in AI runner permits synthetic data only')
  from app.services.adapters import LLMScamClassifier
  enhanced=RiskEngine(cfg,LLMScamClassifier(cfg.llm_url,cfg.llm_key,cfg.llm_model))
  models['C_yatharth_AI']=lambda c:enhanced.analyze(c['message'],FamilyContext(),external_allowed=True)
  ai_meta={'status':'ATTEMPTED','model':cfg.llm_model,'reason':'Synthetic input; requested explicitly with --ai'}
 outputs={}
 for name,model in models.items():
  output=[]
  for case in cases:
   label=select_label(case,mode)
   if label is None:continue
   pred=model(case)
   output.append({'id':case['id'],'group_id':case['group_id'],'language':case['language'],'variant':case['variant'],'buckets':case['buckets'],'expected':label['escalate'],'expected_level':label['risk_level'],'expected_category':label['category'],'expected_signals':label['signals'],'predicted':pred['severity'] in ('HIGH','CRITICAL'),'prediction':pred})
  outputs[name]=output
 if ai:
  states=Counter(r['prediction']['decision_trace']['ai_status'] for r in outputs['C_yatharth_AI'])
  ai_meta['provider_status_counts']=dict(states);ai_meta['status']='COMPLETE' if states.get('USED',0)==len(cases) else 'INCOMPLETE_NOT_COMPARABLE'
 return outputs,ai_meta

def paired_interval(a,b,iterations=1000):
 by_a=defaultdict(list);by_b=defaultdict(list)
 for row in a:by_a[row['group_id']].append(row)
 for row in b:by_b[row['group_id']].append(row)
 groups=sorted(by_a);rng=random.Random(20261005);samples=defaultdict(list)
 for _ in range(iterations):
  chosen=rng.choices(groups,k=len(groups));ma=metrics([r for g in chosen for r in by_a[g]]);mb=metrics([r for g in chosen for r in by_b[g]])
  for key in ['precision','recall','F1','false_positive_rate']:
   if ma[key] is not None and mb[key] is not None:samples[key].append(mb[key]-ma[key])
 def interval(values):
  values=sorted(values);return [values[int(.025*(len(values)-1))],values[int(.975*(len(values)-1))]] if values else None
 return {'method':'paired scenario-group bootstrap; percentile 95%; descriptive, synthetic population only','seed':20261005,'iterations':iterations,'groups':len(groups),'B_minus_A_95_intervals':{k:interval(v) for k,v in samples.items()}}

def diagnostics(cases,outputs):
 lookup={c['id']:c for c in cases};failures=[]
 for model,rows in outputs.items():
  for row in rows:
   if row['expected'] is None or row['expected']==row['predicted']:continue
   c=lookup[row['id']];p=row['prediction'];missing=sorted(set(row['expected_signals'])-set(p['signals']))
   trace=p['decision_trace'];score=p['risk_score'];kind='FN' if row['expected'] else 'FP'
   if model.startswith('A'):
    pattern='keyword_context_failure' if kind=='FP' else 'keyword_coverage_failure';why='Keyword presence ignores context or wording outside its fixed vocabulary.';fix='Compare a context-sensitive classifier at the same false-alert budget.'
   elif c['language']!='English':
    pattern='multilingual_coverage';why='English lexical patterns do not cover the annotated non-English request. Latin acronyms or URLs may still trigger isolated signals.';fix='Collect native-speaker labels and evaluate language-aware detection on a separate held-out set.'
   elif c['variant'] in ['keyword_removed','misspelling','mixed_language','implied_authority','implied_urgency']:
    pattern='adversarial_wording';why='Semantic-preserving paraphrase/obfuscation changes exact pattern matches (equivalence review pending).';fix='Test normalization and contextual models against paired variants; do not tune on this benchmark.'
   elif kind=='FP':
    pattern='contextual_negation_or_quotation';why='Benign explanation/advice contains weighted words; narrow negation handling does not reliably determine who is requesting action.';fix='Distinguish quoted educational content and completed transactions from actionable requests.'
   elif missing:
    pattern='missing_signal_or_indirect_request';why='Semantic label includes indicators not found by the configured patterns; the resulting score stays below 60.';fix='Review missing indicators and evaluate compositional intent/context detection.'
   else:
    pattern='threshold_problem';why='Recognized indicators do not reach the automatic-alert threshold of 60.';fix='Select thresholds only using separate development data and explicit false-alert cost.'
   failures.append({'model':model,'id':c['id'],'kind':kind,'message':c['message'],'expected_label':row['expected_level'],'human_label':c.get('final_label'),'label_status':c['label_status'],'predicted_label':p['severity'],'category':row['expected_category'],'predicted_category':p['risk_type'],'language':c['language'],'variant':c['variant'],'missing_signal':missing,'triggered_signals':p['signals'],'rule_responsible':{'source':'app/services/risk.py' if model=='B_yatharth' else 'evaluation model','missing_pattern_keys':[s for s in missing if s in PATTERNS],'decision_trace':trace},'score':score,'failure_pattern':pattern,'why_detection_failed_or_overreacted':why,'possible_fix':fix,'diagnosis_status':'Code-grounded hypothesis; independent human root-cause review pending'})
 return failures

def analyze(cases,mode='proposed',ai=False):
 outputs,ai_meta=predict(cases,mode,ai)
 result={'dataset_version':'yatharth-v02-synthetic-1.0','label_mode':mode,'human_reviewed_cases':sum(c.get('final_label') is not None for c in cases),'disclaimer':'Assistant-authored synthetic proposed labels. Not real-world or independent human validation. Decision-support score; not a probability.','models':{},'AI':ai_meta}
 for name,rows in outputs.items():
  result['models'][name]={'overall':metrics(rows),'by_language':grouped(rows,'language'),'canonical_by_language':grouped([r for r in rows if r['variant']=='canonical'],'language'),'by_variant':grouped(rows,'variant'),'by_bucket':grouped(rows,'buckets')}
 if outputs['A_keyword']:
  result['paired_comparison']=paired_interval(outputs['A_keyword'],outputs['B_yatharth'])
 b=outputs['B_yatharth'];valid=[r for r in b if r['expected'] is not None]
 result['threshold_sweep_descriptive_only']={str(t):confusion([r['expected'] for r in valid],[r['prediction']['risk_score']>=t for r in valid]) for t in [30,40,50,60,70,80,90]}
 result['severity_decision_table']={level:{'n':len(bucket:=[r for r in valid if r['prediction']['severity']==level]),'proposed_serious':sum(r['expected'] for r in bucket),'proposed_nonserious':sum(not r['expected'] for r in bucket)} for level in ['LOW','MEDIUM','HIGH','CRITICAL']}
 # Analytical upper bound under the actual frozen +10/corroboration gate. Not a model result.
 eligible=[r for r in b if r['expected'] and not r['predicted'] and r['prediction']['risk_score']>=50 and len(r['prediction']['signals'])>=2]
 result['AI_gate_upper_bound']={'recoverable_FN_ids':[r['id'] for r in eligible],'max_additional_TP':len(eligible),'existing_FP_cannot_be_removed':True,'note':'Optimistic bound, NOT an executed AI result. Frozen gate cannot add new signals or reduce scores.'}
 # Paired exact scenario translations; ambiguous scenarios are excluded.
 canonical={r['id']:r for r in b if r['variant']=='canonical'}
 pairs=[]
 for group in sorted({r['group_id'] for r in b}):
  triple=[canonical.get(group+'-'+lang) for lang in ['english','hindi','hinglish']]
  if all(triple) and triple[0]['expected'] is not None:pairs.append({'group_id':group,'expected':triple[0]['expected'],'English':triple[0]['predicted'],'Hindi':triple[1]['predicted'],'Hinglish':triple[2]['predicted']})
 result['translation_pairs']=pairs
 return result,outputs,diagnostics(cases,outputs)

def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,default=ROOT/'cases.json');p.add_argument('--out',type=Path,default=ROOT/'results');p.add_argument('--labels',choices=['proposed','human'],default='proposed');p.add_argument('--ai',action='store_true');a=p.parse_args()
 cases=json.loads(a.dataset.read_text());result,outputs,failures=analyze(cases,a.labels,a.ai)
 result['dataset_sha256']=hashlib.sha256(a.dataset.read_bytes()).hexdigest();result['risk_engine_sha256']=hashlib.sha256(Path('app/services/risk.py').read_bytes()).hexdigest()
 a.out.mkdir(parents=True,exist_ok=True)
 for name,data in [('metrics',result),('predictions',outputs),('failures',failures)]: (a.out/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print(json.dumps({k:v['overall'] for k,v in result['models'].items()},indent=2));print(result['AI'])
if __name__=='__main__':main()
