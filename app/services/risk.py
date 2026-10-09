"""Versioned, deterministic decision support. Scores are NOT fraud probabilities."""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.core.config import Settings

RISK_TYPES = ['NONE', 'UNKNOWN', 'FINANCIAL_SCAM', 'CREDENTIAL_THEFT', 'BANK_IMPERSONATION', 'GOVERNMENT_IMPERSONATION', 'COURIER_SCAM', 'TECH_SUPPORT_SCAM', 'INVESTMENT_SCAM', 'FAMILY_EMERGENCY_IMPERSONATION', 'PHISHING', 'DIGITAL_ARREST_SCAM']
WEIGHTS = {'FINANCIAL_REQUEST':30, 'CREDENTIAL_REQUEST':35, 'URGENCY':15, 'IMPERSONATION':20, 'ACCOUNT_THREAT':20, 'LEGAL_THREAT':20, 'SECRECY':25, 'SUSPICIOUS_LINK':20, 'AUTHORITY_CLAIM':15, 'EMOTIONAL_PRESSURE':10, 'UNUSUAL_REQUEST':30}
PATTERNS = {
    'FINANCIAL_REQUEST': r'\b(?:transfer|send|pay|wire|deposit|purchase|buy)\b.{0,45}(?:money|payment|fee|fine|funds|rupees|rs\.?\s*\d|₹|\$|\d[\d,]*|gift cards?|crypto|bitcoin|upi)|\b(?:payment|upi transfer)\b.{0,25}(?:required|needed|now|immediately)|\b(?:guaranteed returns|double your money)\b',
    'CREDENTIAL_REQUEST': r'\b(?:give|send|share|tell|enter|provide|confirm|verify|submit)\b.{0,45}\b(?:otp|password|pin|cvv|verification code|login details|bank details|card details|your details)\b',
    'URGENCY': r'\b(?:immediately|urgent(?:ly)?|right now|today|within \d+ (?:minutes|hours)|act now|hurry|expires? (?:today|now))\b',
    'IMPERSONATION': r'\b(?:i am|i.m|we are|calling|this is|speaking)\b.{0,35}\b(?:bank|police|rbi|cbi|officer|support|tax department|customs|government)\b',
    'ACCOUNT_THREAT': r'\b(?:account|kyc|electricity|power)\b.{0,45}\b(?:block(?:ed)?|frozen|freez\w*|suspend\w*|expired|disconnect\w*|problem)\b',
    'LEGAL_THREAT': r'\b(?:arrest|crime|criminal|legal action|warrant|money laundering|prosecution)\b',
    'SECRECY': r'\b(?:do not|don.t|never)\s+(?:tell|inform|contact)\b|\b(?:keep (?:it|this) secret|confidential investigation|stay on (?:the )?(?:video )?call)\b',
    'SUSPICIOUS_LINK': r'https?://(?:bit\.ly|tinyurl\.com|[^\s/]*(?:verify|login|kyc|claim|secure|reward|update)[^\s/]*|(?:\d{1,3}\.){3}\d{1,3})(?:/|\b)|https?://[^\s]+\.(?:xyz|top|click)(?:/|\b)',
    'AUTHORITY_CLAIM': r'\b(?:rbi|cbi|police|government|tax department|bank officer|customs|kyc)\b',
    'EMOTIONAL_PRESSURE': r'\b(?:accident|hospital|save me|help me|your (?:son|daughter)|injured|stranded)\b',
    'UNUSUAL_REQUEST': r'\b(?:remote access|anydesk|teamviewer|screen sharing|unknown number|strange message|guaranteed returns|double your money)\b',
}

@dataclass(frozen=True)
class FamilyContext:
    family_id: str = ''
    protected_person_id: str = ''
    caregiver_count: int = 0
    consent_id: str = ''
    previous_risk_count: int = 0

class Classification(BaseModel):
    model_config = ConfigDict(extra='forbid')
    risk_type: Literal['NONE', 'UNKNOWN', 'FINANCIAL_SCAM', 'CREDENTIAL_THEFT', 'BANK_IMPERSONATION', 'GOVERNMENT_IMPERSONATION', 'COURIER_SCAM', 'TECH_SUPPORT_SCAM', 'INVESTMENT_SCAM', 'FAMILY_EMERGENCY_IMPERSONATION', 'PHISHING', 'DIGITAL_ARREST_SCAM']
    confidence: float = Field(ge=0, le=1)
    signals: list[str] = Field(max_length=12)
    reasoning_summary: str = Field(default='', max_length=500)
    recommended_action: str = Field(default='', max_length=500)

class ScamClassifier(Protocol):
    def analyze(self, message: str, context: FamilyContext) -> Classification: ...

def normalize(text):
    return re.sub(r'\s+', ' ', ''.join(c for c in unicodedata.normalize('NFKC', text) if unicodedata.category(c) != 'Cf')).lower().strip()

def detect(text):
    # Narrow negative request patterns avoid counting bank safety warnings as requests.
    text = re.sub(r'\b(?:never|do not|don.t)\s+(?:share|send|give|provide|tell|enter)\b(?=[^.!?;]*\b(?:otp|password|pin|cvv|verification code|bank details)\b)[^.!?;]*', '', text)
    text = re.sub(r'\b(?:we|banks?)\s+(?:will )?never\s+(?:ask|request)\b[^.!?;]*', '', text)
    text = re.sub(r'\bno (?:payment|fee) is required\b', '', text)
    signals = [name for name, pattern in PATTERNS.items() if re.search(pattern, text)]
    if 'IMPERSONATION' in signals and 'bank' in text and 'AUTHORITY_CLAIM' not in signals:
        signals.append('AUTHORITY_CLAIM')
    return signals

def category(text, signals):
    s = set(signals)
    if not s: return 'NONE'
    if 'LEGAL_THREAT' in s and ('digital arrest' in text or ('SECRECY' in s and 'AUTHORITY_CLAIM' in s)): return 'DIGITAL_ARREST_SCAM'
    if ('bank' in text or 'kyc' in text) and s & {'IMPERSONATION', 'ACCOUNT_THREAT', 'CREDENTIAL_REQUEST'}: return 'BANK_IMPERSONATION'
    if re.search(r'\b(police|rbi|cbi|government|tax department)\b', text) and s & {'LEGAL_THREAT', 'FINANCIAL_REQUEST', 'CREDENTIAL_REQUEST'}: return 'GOVERNMENT_IMPERSONATION'
    if re.search(r'\b(courier|parcel|customs|package)\b', text) and s & {'FINANCIAL_REQUEST', 'SUSPICIOUS_LINK'}: return 'COURIER_SCAM'
    if re.search(r'\b(remote access|anydesk|teamviewer|computer infected|tech support)\b', text): return 'TECH_SUPPORT_SCAM'
    if re.search(r'\b(investment|guaranteed returns|double your money)\b', text): return 'INVESTMENT_SCAM'
    if 'EMOTIONAL_PRESSURE' in s and 'FINANCIAL_REQUEST' in s: return 'FAMILY_EMERGENCY_IMPERSONATION'
    if 'CREDENTIAL_REQUEST' in s: return 'CREDENTIAL_THEFT'
    if 'SUSPICIOUS_LINK' in s: return 'PHISHING'
    if 'FINANCIAL_REQUEST' in s: return 'FINANCIAL_SCAM'
    return 'UNKNOWN'

class RuleBasedScamClassifier:
    def analyze(self, message, context):
        text = normalize(message)
        signals = detect(text)
        return Classification(risk_type=category(text, signals), confidence=0.5 if not signals else min(0.85, 0.4 + len(signals)*0.08), signals=signals)

def severity(score, settings):
    if score >= settings.critical_threshold: return 'CRITICAL'
    if score >= settings.high_threshold: return 'HIGH'
    if score >= settings.medium_threshold: return 'MEDIUM'
    return 'LOW'

class RiskEngine:
    def __init__(self, settings: Settings, classifier=None):
        self.settings, self.optional = settings, classifier
        self.rules = RuleBasedScamClassifier()

    def analyze(self, message, context, external_allowed=False):
        result = self.rules.analyze(message, context)
        weights = {s:WEIGHTS[s] for s in result.signals}
        # A promise of returns is one unusual claim, not independent payment evidence.
        if 'FINANCIAL_REQUEST' in weights and 'UNUSUAL_REQUEST' in weights:
            without_promise = re.sub(r'\b(?:guaranteed returns|double your money)\b', '', normalize(message))
            if not re.search(PATTERNS['FINANCIAL_REQUEST'], without_promise):
                weights.pop('FINANCIAL_REQUEST')
                result.signals.remove('FINANCIAL_REQUEST')
        score = min(100, sum(weights.values()))
        combinations = {}
        if {'FINANCIAL_REQUEST', 'EMOTIONAL_PRESSURE', 'URGENCY'} <= set(result.signals):
            combinations['URGENT_EMERGENCY_PAYMENT'] = 10
        score = min(100, score + sum(combinations.values()))
        # Corroboration needed; isolated words/signals cannot cause automatic alerts.
        if len(weights) < 2: score = min(score, self.settings.high_threshold-1)
        ai_status, bonus = 'DISABLED', 0
        if external_allowed and (self.settings.llm_enabled or self.settings.openworker_enabled):
            ai_status = 'UNAVAILABLE'
            if self.optional:
                try:
                    ai = Classification.model_validate(self.optional.analyze(message, context))
                    if any(x not in WEIGHTS for x in ai.signals): raise ValueError('Unknown signal')
                    # AI can add at most 10 corroboration points, never reduce strong rule evidence.
                    overlap = set(ai.signals) & set(result.signals)
                    if ai.confidence >= .8 and len(overlap) >= 2 and score >= 30:
                        bonus = 10
                    ai_status = 'USED'
                except Exception:
                    # Never log provider exception bodies: they may repeat private messages.
                    ai_status = 'FAILED_FALLBACK'
        elif not external_allowed and (self.settings.llm_enabled or self.settings.openworker_enabled):
            ai_status = 'CONSENT_DISABLED'
        final = min(100, score + bonus)
        explanation = ('Potential scam indicators detected: ' + ', '.join(s.lower().replace('_', ' ') for s in result.signals) + '.') if result.signals else 'No configured scam indicators detected. This does not establish that a message is safe.'
        recommendation = 'Pause before acting. Contact the person or institution using an independently verified number. Do not share credentials or transfer money until verified.' if final >= 30 else 'Stay cautious. Independently verify any unexpected request.'
        return dict(risk_type=result.risk_type, risk_score=final, severity=severity(final, self.settings), confidence=result.confidence, signals=result.signals, explanation=explanation, recommended_action=recommendation, model_version='rules-0.1+decision-0.1', decision_trace={'weights':weights, 'combinations':combinations, 'rule_score':score, 'ai_bonus':bonus, 'ai_status':ai_status, 'high_threshold':self.settings.high_threshold, 'critical_threshold':self.settings.critical_threshold, 'prior_risks':context.previous_risk_count, 'context_policy':'metadata only; no history bonus', 'confidence_kind':'uncalibrated rule-evidence strength, not fraud probability'})
