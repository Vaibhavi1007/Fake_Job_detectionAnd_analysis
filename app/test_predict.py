from predict import get_risk
from flags import get_flags

posts = [
    "Work from home earn 50000 per week no experience pay registration fee contact on whatsapp",
    "Earn Rs 5000 per day, no experience needed. Pay Rs 500 registration fee. Contact on WhatsApp. Apply now, only 5 seats left!",
    "Software engineer with 3 years of Python experience at our Pune office. Health insurance and paid leave. Apply through our careers page after a technical and HR round.",
]
for t in posts:
    print(get_risk(description=t, flags=get_flags(t)))
    print()