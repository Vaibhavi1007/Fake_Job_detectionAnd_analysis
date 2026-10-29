"""HireTrust website (Streamlit).

Run from the `app` folder, with the virtual environment active:
    streamlit run app.py
Needs predict.py, flags.py and the models/ folder next to this file.
"""
import streamlit as st

st.set_page_config(page_title="HireTrust", page_icon="🛡️", layout="centered")

try:
    from predict import get_risk
    from flags import get_flags
except Exception as e:                       # missing model file, wrong versions, etc.
    st.error("Could not load the model files. Check that the `models` folder is next to "
             "`app.py` and that the package versions match `requirements.txt`.")
    st.code(str(e))
    st.stop()

EXAMPLES = {
    "scam": {
        "title": "Data Entry Executive - Work From Home",
        "company": "",
        "description": ("Earn Rs 5000 per day from home, no experience needed. Pay a one-time "
                        "registration fee of Rs 500 to confirm your seat. Contact us on WhatsApp "
                        "or mail hr.jobs2024@gmail.com. Apply now, only 5 seats left!"),
        "requirements": "",
        "benefits": "",
    },
    "genuine": {
        "title": "Software Engineer",
        "company": "Acme Technologies is a software company based in Pune.",
        "description": ("We are looking for a software engineer to build backend services in Python. "
                        "You will work in a team of ten and join code reviews. Applications go "
                        "through our careers page, followed by a technical round and an HR round."),
        "requirements": "Three years of Python experience and a bachelor's degree.",
        "benefits": "Health insurance and paid leave.",
    },
}
FIELDS = ["title", "company", "description", "requirements", "benefits"]


def load_example(name):
    for f in FIELDS:
        st.session_state[f] = EXAMPLES[name][f]


def clear_fields():
    for f in FIELDS:
        st.session_state[f] = ""


for f in FIELDS:
    st.session_state.setdefault(f, "")

# ---------- header ----------
st.title("HireTrust")
st.write("Paste a job posting to see its fake-job **risk score** and the reasons behind it.")

with st.sidebar:
    st.header("About")
    st.write("HireTrust combines a machine-learning model (trained on the EMSCAD job-posting "
             "dataset) with scam red-flag rules.")
    st.write("**Limits:** the dataset is about 10 years old, and the model can over-score some "
             "genuine posts, such as clerical jobs. Treat the result as a warning sign, "
             "not proof.")
    st.write("Never pay money to get a job.")

# ---------- input ----------
c1, c2, c3 = st.columns(3)
c1.button("Load scam example", on_click=load_example, args=("scam",))
c2.button("Load genuine example", on_click=load_example, args=("genuine",))
c3.button("Clear", on_click=clear_fields)

title = st.text_input("Job title", key="title")
description = st.text_area("Job description", key="description", height=200)
with st.expander("More fields (optional)"):
    company = st.text_area("Company profile", key="company", height=100)
    requirements = st.text_area("Requirements", key="requirements", height=100)
    benefits = st.text_area("Benefits", key="benefits", height=100)

# ---------- result ----------
if st.button("Check this post", type="primary"):
    raw_text = " ".join([title, company, description, requirements, benefits]).strip()
    if len(raw_text.split()) < 5:
        st.warning("Please enter a job description with at least a few words.")
    else:
        try:
            # company_profile=None: a blank box is not treated as 'no company details'
            flags = get_flags(raw_text)
            result = get_risk(title=title, company_profile=company, description=description,
                              requirements=requirements, benefits=benefits, flags=flags)
        except Exception as e:
            st.error("Something went wrong while scoring this post.")
            st.code(str(e))
        else:
            score, level = result["score"], result["level"]
            st.subheader(f"Risk score: {score} / 100")
            st.progress(min(max(score, 0), 100) / 100)
            if level == "High":
                st.error("High risk: this post shows strong warning signs.")
            elif level == "Medium":
                st.warning("Medium risk: some warning signs. Check the company before applying.")
            else:
                st.success("Low risk signals found. This does not guarantee the post is genuine.")

            st.markdown("**Scam warning signs found (rules)**")
            if flags:
                for f in flags:
                    st.write("- " + f)
            else:
                st.write("None of the rule-based signs were found.")

            st.markdown("**What the model noticed**")
            model_reasons = result["reasons"][len(flags):]
            if level == "Low":
                st.write("No strong warning signs in the wording.")
            elif model_reasons:
                for r in model_reasons:
                    st.write("- " + r)
            else:
                st.write("No single word stood out.")

            st.caption("Always verify the company independently, through its official website, "
                       "before sharing documents or paying anything.")
