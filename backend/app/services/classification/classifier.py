import re
from typing import Tuple, List, Dict, Optional
from backend.app.schemas.models import ClassificationResult

INTENT_KEYWORDS: Dict[str, List[str]] = {
    "ACCOUNT_SECURITY": ["hacked", "compromised", "unauthorized", "stolen", "fraud", "breach", "suspicious login", "password reset requested by someone else"],
    "PAYMENT_FAILURE": ["payment failed", "transaction declined", "card rejected", "deducted but not credited", "charged twice", "upi error", "checkout failed"],
    "PAYMENT_DUPLICATE": ["charged twice", "double payment", "duplicate charge", "debited two times"],
    "REFUND_REQUEST": ["refund", "money back", "reimbursement", "cancel order and refund", "return request"],
    "LOGIN_ISSUE": ["cannot login", "otp not received", "password reset", "account locked", "2fa error", "session expired"],
    "TECHNICAL_ISSUE": [
        "crash", "bug", "500 internal server error", "api failure", "blank screen", "app not opening", "exception",
        "no internet", "no network", "internet issue", "fiber", "wifi", "network down", "connectivity", "outage", "disconnection", "router"
    ],
    "BILLING_QUERY": ["invoice", "tax receipt", "pricing", "subscription charge", "gst details", "statement"],
    "ORDER_STATUS": ["where is my order", "shipping delay", "tracking number", "courier status", "delivery time"],
    "ACCOUNT_UPDATE": ["change email", "update phone number", "address correction", "kyc update", "profile modification"],
    "GENERAL_ENQUIRY": ["how to use", "contact support", "office address", "working hours", "features list"]
}

INTENT_SKILL_MAP: Dict[str, str] = {
    "ACCOUNT_SECURITY": "SECURITY_FORENSICS",
    "PAYMENT_FAILURE": "PAYMENT_GATEWAY",
    "PAYMENT_DUPLICATE": "PAYMENT_GATEWAY",
    "TECHNICAL_ISSUE": "INFRA_SYSADMIN",
    "REFUND_REQUEST": "BILLING_OPERATIONS",
    "BILLING_QUERY": "BILLING_OPERATIONS",
    "LOGIN_ISSUE": "CUSTOMER_SUCCESS",
    "ORDER_STATUS": "CUSTOMER_SUCCESS",
    "ACCOUNT_UPDATE": "CUSTOMER_SUCCESS",
    "GENERAL_ENQUIRY": "CUSTOMER_SUCCESS"
}

# Unicode scripts and romanized indicators for multilingual detection
LANGUAGE_INDICATORS: Dict[str, List[str]] = {
    "te": [r"[\u0C00-\u0C7F]", r"\bnamaskaram\b", r"\bela unnaru\b", r"\bnenu\b", r"\bsahayam\b", r"\bkavali\b", r"\bdabbu\b", r"\bchudandi\b", r"\bcheyandi\b"],
    "hi": [r"[\u0900-\u097F]", r"\bnamaste\b", r"\bmadad\b", r"\bchahiye\b", r"\bpaisa\b", r"\bnahi\b", r"\bhua\b", r"\bkripya\b", r"\bmera\b", r"\bkhata\b", r"\bkhate\b"],
    "ta": [r"[\u0B80-\u0BFF]", r"\bvanakkam\b", r"\budavi\b", r"\bthevai\b", r"\bpanam\b", r"\bvaravillai\b", r"\bennoda\b", r"\bseiyavum\b"],
    "kn": [r"[\u0C80-\u0CFF]", r"\bnamaskara\b", r"\bsahaya\b", r"\bbeku\b", r"\bhana\b", r"\bbandilla\b", r"\bmadikodi\b", r"\bnanna\b"]
}

DURATION_PATTERN = re.compile(r"(\d+)\s*(days?|hours?|weeks?|months?)", re.IGNORECASE)
RECURRENCE_PATTERN = re.compile(r"(multiple times|repeatedly|again and again|recurring|every week|frequently|every month|multiple days)", re.IGNORECASE)

class ClassificationEngine:
    @staticmethod
    def detect_language(text: str) -> str:
        text_lower = text.lower()
        for lang, patterns in LANGUAGE_INDICATORS.items():
            for pat in patterns:
                if re.search(pat, text_lower if not pat.startswith("[") else text):
                    return lang
        return "en"

    @staticmethod
    def analyze_sentiment(text: str) -> float:
        """
        Analyzes message sentiment returning a score in [-1.0, 1.0].
        Positive values indicate satisfaction/politeness.
        Negative values indicate frustration, anger, or urgency.
        """
        text_lower = text.lower()
        negative_words = [
            "terrible", "worst", "unacceptable", "horrible", "angry", "frustrated", "disappointed",
            "useless", "pathetic", "hate", "stolen", "fraud", "scam", "broken", "failed", "poor",
            "ridiculous", "urgent", "no internet", "cheated", "down", "not working", "again and again"
        ]
        positive_words = [
            "thank", "thanks", "great", "excellent", "awesome", "good", "helpful", "resolved",
            "appreciate", "quick", "fast", "polite", "glad", "satisfied", "pleased", "wonderful"
        ]
        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)
        
        total = neg_count + pos_count
        if total == 0:
            return 0.0
        score = (pos_count - neg_count) / total
        return round(float(max(-1.0, min(1.0, score))), 2)

    @classmethod
    def classify(cls, subject: str, body: str) -> ClassificationResult:
        full_text = f"{subject} {body}".lower()
        detected_lang = cls.detect_language(full_text)
        
        # 1. Multi-Intent Extraction
        all_detected: List[Tuple[str, int]] = []
        intent_category_map = {
            "ACCOUNT_SECURITY": "SECURITY",
            "PAYMENT_FAILURE": "BILLING",
            "PAYMENT_DUPLICATE": "BILLING",
            "REFUND_REQUEST": "BILLING",
            "LOGIN_ISSUE": "AUTH",
            "TECHNICAL_ISSUE": "TECH",
            "BILLING_QUERY": "BILLING",
            "ORDER_STATUS": "OPERATIONS",
            "ACCOUNT_UPDATE": "AUTH",
            "GENERAL_ENQUIRY": "GENERAL"
        }

        default_intent_priorities = {
            "ACCOUNT_SECURITY": "P1",
            "PAYMENT_FAILURE": "P2",
            "PAYMENT_DUPLICATE": "P2",
            "TECHNICAL_ISSUE": "P2",
            "REFUND_REQUEST": "P3",
            "LOGIN_ISSUE": "P3",
            "BILLING_QUERY": "P3",
            "ORDER_STATUS": "P3",
            "ACCOUNT_UPDATE": "P4",
            "GENERAL_ENQUIRY": "P4"
        }

        for intent, keywords in INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in full_text)
            if hits > 0:
                all_detected.append((intent, hits))

        # Sort by hit count descending
        all_detected.sort(key=lambda x: x[1], reverse=True)

        if all_detected:
            best_intent, highest_hits = all_detected[0]
            best_category = intent_category_map.get(best_intent, "GENERAL")
            all_intent_names = [item[0] for item in all_detected]
        else:
            best_intent = "GENERAL_ENQUIRY"
            best_category = "GENERAL"
            highest_hits = 0
            all_intent_names = ["GENERAL_ENQUIRY"]

        # Confidence Calculation
        if highest_hits == 0:
            confidence = 0.40 # Ambiguous / Unmatched
        elif len(all_detected) > 1 and all_detected[0][1] == all_detected[1][1]:
            confidence = 0.60 # Tie between multiple intents
        else:
            confidence = min(0.98, 0.70 + (highest_hits * 0.10))

        needs_manual_review = bool(confidence < 0.65)
        computed_priority = default_intent_priorities.get(best_intent, "P3")
        applied_safety_rules = []

        # 2. Extract Duration and Recurrence
        duration_match = DURATION_PATTERN.search(full_text)
        duration_text = duration_match.group(0) if duration_match else None
        is_recurring = bool(RECURRENCE_PATTERN.search(full_text))

        # 3. Customer Impact Assessment
        customer_impact = "MEDIUM"
        if best_category == "SECURITY" or computed_priority == "P1":
            customer_impact = "CRITICAL"
        elif is_recurring or (duration_match and int(duration_match.group(1)) >= 2):
            customer_impact = "HIGH"
            # Elevate priority if recurring technical or billing issue
            if computed_priority in ["P3", "P4"]:
                computed_priority = "P2"
        elif computed_priority == "P4":
            customer_impact = "LOW"

        # 4. Hard Deterministic Safety Rules (Cannot be downgraded by AI)
        security_triggers = ["stolen", "unauthorized", "hacked", "fraud", "compromised", "breach"]
        if any(trig in full_text for trig in security_triggers) or best_intent == "ACCOUNT_SECURITY":
            computed_priority = "P1"
            best_intent = "ACCOUNT_SECURITY"
            best_category = "SECURITY"
            customer_impact = "CRITICAL"
            needs_manual_review = False # Immediate forced override, no ambiguity
            applied_safety_rules.append("SR-001: HARD_CRITICAL_SECURITY_OVERRIDE (Forced P1)")

        if any(w in full_text for w in ["production down", "outage", "system unavailable", "emergency"]):
            computed_priority = "P1"
            customer_impact = "CRITICAL"
            needs_manual_review = False
            applied_safety_rules.append("SR-002: HARD_CRITICAL_INCIDENT_OVERRIDE (Forced P1)")

        required_skill = INTENT_SKILL_MAP.get(best_intent, "CUSTOMER_SUCCESS")

        return ClassificationResult(
            intent_id=best_intent,
            category=best_category,
            confidence=round(confidence, 2),
            language_code=detected_lang,
            priority=computed_priority,
            required_skill_id=required_skill,
            all_detected_intents=all_intent_names,
            duration_text=duration_text,
            is_recurring=is_recurring,
            customer_impact=customer_impact,
            needs_manual_review=needs_manual_review,
            applied_safety_rules=applied_safety_rules,
            classification_method="HYBRID_RULE_ENGINE"
        )
