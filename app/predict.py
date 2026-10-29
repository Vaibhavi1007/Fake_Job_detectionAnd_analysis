"""HireTrust: risk scoring for a job posting.

Put these files in a folder called `models/` next to this script:
    final_model.joblib   (classifier, used for the risk score)
    final_tfidf.joblib   (vectorizer)
    explain_lr.joblib    (OPTIONAL. Only needed if final_model is not a
                          Logistic Regression, e.g. Random Forest / XGBoost)
"""
import os
import re

import joblib

# IMPORTANT: this must match how the model was TRAINED.
#   False -> model trained on the raw dataset text (Gauri's current files)
#   True  -> model trained on clean_jobs.csv (e.g. from notebook 03)
CLEAN_INPUT = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

model = joblib.load(os.path.join(MODEL_DIR, "final_model.joblib"))
tfidf = joblib.load(os.path.join(MODEL_DIR, "final_tfidf.joblib"))

_explain_path = os.path.join(MODEL_DIR, "explain_lr.joblib")
if os.path.exists(_explain_path):
    explainer = joblib.load(_explain_path)
elif hasattr(model, "coef_"):
    explainer = model                      # a Logistic Regression explains itself
else:
    explainer = None                       # no per-word explanation available

WORDS = tfidf.get_feature_names_out()
FAKE_IDX = list(model.classes_).index(1)


def clean_text(t):
    """Same cleaning that was used to make clean_jobs.csv."""
    t = t.lower()
    t = re.sub(r"http\S+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def get_risk(title="", company_profile="", description="",
             requirements="", benefits="", flags=None):
    text = " ".join(str(x or "") for x in
                    [title, company_profile, description, requirements, benefits])
    if not text.strip():
        raise ValueError("Please provide some job posting text.")

    X = tfidf.transform([clean_text(text) if CLEAN_INPUT else text])
    prob = float(model.predict_proba(X)[0][FAKE_IDX])
    score = round(prob * 100)
    level = "Low" if score < 33 else "Medium" if score < 66 else "High"

    reasons = list(flags or [])            # Shreya's rule flags go here
    if explainer is not None:
        contrib = X.multiply(explainer.coef_[0]).tocoo()
        pairs = sorted(((WORDS[j], v) for j, v in zip(contrib.col, contrib.data) if v > 0),
                       key=lambda p: p[1], reverse=True)
        top_words = [w for w, _ in pairs[:5]]
        if top_words:
            reasons.append("Words that raised the risk: " + ", ".join(top_words))

    return {"score": score, "level": level, "reasons": reasons,
            "fake_probability": round(prob, 4)}
