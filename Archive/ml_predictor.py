import os
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

model = joblib.load(os.path.join(MODEL_DIR, "fake_job_model.pkl"))
tfidf = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))

def predict_job(title="", company_profile="", description="",
                requirements="", benefits=""):
    text = " ".join(str(x or "") for x in [
        title, company_profile, description, requirements, benefits
    ])

    if not text.strip():
        raise ValueError("Please provide some job posting text.")

    features = tfidf.transform([text])
    prediction = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0]
    fake_index = list(model.classes_).index(1)

    return {
        "prediction": "Potentially Fake Job" if prediction == 1 else "Likely Real Job",
        "fake_probability": round(float(probabilities[fake_index]), 4)
}
