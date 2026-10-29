"""HireTrust: risk scoring for a job posting.

Put these files in a folder called `models/` next to this script:
    final_tfidf.joblib   (vectorizer)                       REQUIRED
    final_xgb.json       (XGBoost model, safe format)       use this if it exists
    final_model.joblib   (classifier, used if no .json)     fallback
    explain_lr.joblib    (Logistic Regression, finds the risky words)
"""
import os
import re

import joblib

# IMPORTANT: this must match how the model was TRAINED.
#   False -> model trained on the raw dataset text (Gauri's first files)
#   True  -> model trained on clean_jobs.csv (notebook 03)
CLEAN_INPUT = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")


def _path(name):
    return os.path.join(MODEL_DIR, name)


tfidf = joblib.load(_path("final_tfidf.joblib"))

# The classifier: prefer the XGBoost JSON file, otherwise the joblib file.
_booster = None
model = None
if os.path.exists(_path("final_xgb.json")):
    import xgboost as xgb
    _booster = xgb.Booster()
    _booster.load_model(_path("final_xgb.json"))
else:
    model = joblib.load(_path("final_model.joblib"))

# The explainer: a Logistic Regression that has a weight for every word.
if os.path.exists(_path("explain_lr.joblib")):
    explainer = joblib.load(_path("explain_lr.joblib"))
elif model is not None and hasattr(model, "coef_"):
    explainer = model
else:
    explainer = None

WORDS = tfidf.get_feature_names_out()
FAKE_IDX = list(model.classes_).index(1) if model is not None else 1


def clean_text(t):
    """Same cleaning that was used to make clean_jobs.csv."""
    t = t.lower()
    t = re.sub(r"http\S+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _fake_probability(X):
    if _booster is not None:
        import xgboost as xgb
        return float(_booster.predict(xgb.DMatrix(X))[0])
    return float(model.predict_proba(X)[0][FAKE_IDX])


def get_risk(title="", company_profile="", description="",
             requirements="", benefits="", flags=None):
    text = " ".join(str(x or "") for x in
                    [title, company_profile, description, requirements, benefits])
    if not text.strip():
        raise ValueError("Please provide some job posting text.")

    X = tfidf.transform([clean_text(text) if CLEAN_INPUT else text])
    prob = _fake_probability(X)
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
