"""HireTrust scam red-flag rules.

Signs and threat scores come from Shreya's sheet (Hiretrust_scam_signs).
Run on the RAW job-post text (cleaning removes emails and links).
"""
import re
from difflib import SequenceMatcher

FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
                      "rediffmail.com", "ymail.com", "proton.me", "protonmail.com"}

# Example list. Shreya: extend with real companies that scammers copy.
KNOWN_DOMAINS = ["infosys.com", "tcs.com", "wipro.com", "accenture.com", "cognizant.com",
                 "hcltech.com", "capgemini.com", "techmahindra.com", "amazon.com",
                 "google.com", "microsoft.com", "deloitte.com", "ibm.com", "flipkart.com"]

# (sign, category, threat score, regex). Lookalike domain, no company profile,
# vague description and different logo are handled separately below.
RULES = [
    ("Asks for bank/card details", "Identity", 95,
     r"bank\s+(account|details|statement)|card\s+number|\bcvv\b|atm\s+pin|\botp\b|credit\s+card|debit\s+card"),
    ("Registration/application fee", "Money", 90,
     r"(registration|training|processing|joining|application|kit)\s+(fee|fees|charges?)"
     r"|pay\s+(rs\.?|inr|₹)\s*\d+.{0,40}(confirm|apply|register)"),
    ("Security deposit", "Money", 90,
     r"(security|refundable)\s+deposit"),
    ("Pay by UPI/QR", "Money", 85,
     r"\bupi\b|google\s*pay|\bgpay\b|phonepe|paytm|qr\s*code|scan\s+(this|the)\s+qr"),
    ("Asks for Aadhaar/PAN early", "Identity", 80,
     r"aadhaar|aadhar|pan\s+card"),
    ("WhatsApp/Telegram only", "Channel", 50,
     r"\b(whatsapp|telegram)\b"),
    ("No interview / instant selection", "Too good to be true", 50,
     r"no\s+interview|instant\s+selection|direct\s+joining|instant\s+offer"),
    ("Free email", "Email/Website", 50, None),   # handled via email domains
    ("Guaranteed job", "Too good to be true", 45,
     r"\d+\s*%\s*(placement|job)\s+guarantee|guaranteed\s+(job|placement|income|salary)|job\s+confirmed\s+after\s+payment"),
    ("Urgency/asks for limited seats", "Pressure", 25,
     r"(only\s+)?\d+\s+(seats?|vacancies|positions?)\s+left|last\s+chance|apply\s+(today|now|immediately)|urgent(ly)?\s+hiring|limited\s+seats"),
]
COMPILED = [(s, c, sc, re.compile(p, re.I) if p else None) for s, c, sc, p in RULES]

AFTER_OFFER = re.compile(r"after\s+(you\s+)?(accept|selection|joining|the\s+offer|offer)", re.I)
EMAIL_RX = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", re.I)
URL_RX = re.compile(r"https?://(?:www\.)?([\w-]+(?:\.[\w-]+)+)", re.I)
TWO_PART_TLDS = {"co.in", "ac.in", "org.in", "gov.in", "net.in", "co.uk"}


def _registrable(domain):
    parts = domain.lower().strip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_PART_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _domains(text):
    found = set(_registrable(d) for d in EMAIL_RX.findall(text))
    found |= set(_registrable(d) for d in URL_RX.findall(text))
    return found


def _lookalike(domains):
    for d in domains:
        if d in FREE_EMAIL_DOMAINS or d in KNOWN_DOMAINS:
            continue
        for k in KNOWN_DOMAINS:
            if 0.85 <= SequenceMatcher(None, d, k).ratio() < 1.0:
                return True
    return False


def detect(text, company_profile=None):
    """Return a list of (sign, category, threat_score) for the signs found."""
    text = str(text or "")
    hits = []
    domains = _domains(text)
    for sign, cat, score, rx in COMPILED:
        if sign == "Free email":
            if any(d in FREE_EMAIL_DOMAINS for d in domains):
                hits.append((sign, cat, score))
        elif rx.search(text):
            if sign == "Asks for Aadhaar/PAN early" and AFTER_OFFER.search(text):
                continue    # normal onboarding, not an early request
            hits.append((sign, cat, score))
    if _lookalike(domains):
        hits.append(("Lookalike company domain", "Email/Website", 95))
    if company_profile is not None and not str(company_profile).strip():
        hits.append(("No company name or profile", "Content", 55))
    if 0 < len(text.split()) < 20:
        hits.append(("Very short or vague description", "Content", 25))
    return sorted(hits, key=lambda h: -h[2])


def get_flags(text, company_profile=None):
    """List of plain sentences, for the 'reasons' part of get_risk(flags=...)."""
    return [f"{s} (threat {sc}/100)" for s, c, sc in detect(text, company_profile)]


def rule_score(text, company_profile=None):
    """Combine threat scores into 0-100: 1 - product(1 - score/100).
    The scores are expert estimates, not calibrated probabilities, so validate
    this on real posts before using it to change the final risk level."""
    left = 1.0
    for _, _, sc in detect(text, company_profile):
        left *= 1 - sc / 100
    return round((1 - left) * 100)
