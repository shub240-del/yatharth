"""Internal synthetic prototype evaluation, not real-world validation."""
import json
from pathlib import Path
from app.core.config import Settings
from app.services.risk import RiskEngine, FamilyContext

DATA = Path(__file__).with_name('cases.json')

def evaluate(cases=None):
    cases = cases if cases is not None else json.loads(DATA.read_text())
    engine = RiskEngine(Settings(llm_enabled=False, openworker_enabled=False))
    counts = dict(true_positives=0,false_positives=0,true_negatives=0,false_negatives=0)
    mismatches, severity_correct = [], 0
    for case in cases:
        result = engine.analyze(case['message'], FamilyContext())
        actual = case['label'] in ('HIGH_RISK','CRITICAL_RISK')
        predicted = result['severity'] in ('HIGH','CRITICAL')
        key = ('true_positives' if actual else 'false_positives') if predicted else ('false_negatives' if actual else 'true_negatives')
        counts[key] += 1
        target = 'LOW' if case['label'] in ('SAFE','LOW_RISK') else case['label'].removesuffix('_RISK')
        severity_correct += result['severity'] == target
        if target != result['severity']:
            mismatches.append({'id':case['id'],'expected':target,'actual':result['severity'],'score':result['risk_score']})
    tp,fp,fn = counts['true_positives'],counts['false_positives'],counts['false_negatives']
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    return {'notice':'Internal prototype evaluation. Hand-authored synthetic cases, not a held-out real-world benchmark.', 'cases':len(cases), **counts,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'high_critical_recall':recall,'severity_accuracy':severity_correct/len(cases) if cases else 0,'severity_mismatches':mismatches}

if __name__ == '__main__':
    print('YATHARTH RISK ENGINE EVALUATION')
    print(json.dumps(evaluate(),indent=2))
