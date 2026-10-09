# Pre-evaluation protocol

All 260 cases and proposed labels are frozen before predictions are generated.
V0.1 product code, thresholds and normalization remain byte-for-byte unchanged.
This is an assistant-authored synthetic challenge set, NOT independent human
validation, and NOT a population sample. The author inspected V0.1 rules, so the
benchmark cannot be called blinded or held out from the author.

Label policy (based on text available, not engine output):
- LOW: routine information, receipts, or explicit safety education.
- MEDIUM: isolated suspicious request without enough corroboration for an alert.
- HIGH: actionable dangerous request with corroborating coercion, identity claim,
  credential misuse or anomalous payment mechanism.
- CRITICAL: coercive authority/emergency request plus secrecy or legal threat.
- AMBIGUOUS: insufficient evidence or reviewer disagreement. Exclude from binary
  metrics, report count and predicted alert rate separately.

Primary endpoint: caregiver escalation precision/recall/FPR. Positive is an
independent proposed HIGH or CRITICAL label. Also report HIGH/CRITICAL detection
recall separately, exact severity, category accuracy and signal precision/recall.
Null denominators remain null. No probability calibration claim is permitted.

Compare A: small English keyword OR baseline (evaluation only); B: unchanged
Yatharth; C: existing optional-AI path only if configured. Do not silently report
rules fallback as a successful AI evaluation. Add a language-parity keyword
sensitivity baseline to avoid mistaking English vocabulary coverage for intelligence.

Paired translations and adversarial variants share group_id. Use group-level
bootstrap intervals for A/B metric differences. Do not treat 260 correlated rows
as 260 independent people. No hyperparameters may be selected from this challenge
set. Score-threshold sweeps are descriptive only.

Humans review blank, shuffled JSONL packets independently, with no proposed label
or model prediction. Two different reviewer IDs are required. Exact disagreement
on risk/category/escalation/signals yields final AMBIGUOUS, retaining both raw
annotations. Human-only evaluation must be separate and cannot substitute proposals.
