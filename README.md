# StrokeScope: stroke risk screening application

**Live app:** [strokescope-screening-application.streamlit.app](https://strokescope-screening-application.streamlit.app/) · **Notebook and project folder:** [AIOPS-Portfolio-Projects](https://github.com/ahmadhassan-aiops/AIOPS-Portfolio-Projects/tree/main/2.%20Machine%20Learning%20Projects/Stroke%20Prediction)

A stroke risk screening aid, by **Ahmad Hassan** (AI Engineer). It decides **who should be checked first**, and it is
built around the error that matters most in screening: a stroke patient who is missed. A tuned logistic regression,
trained on 4,087 patients and tested once on 1,022 it never saw, **finds 42 of the 50 stroke patients (recall 84%)**
at its screening line, against 9 of 50 for the first version of the model on the same patients. Its risks are
calibrated, and every score splits exactly into one odds multiplier per factor.

The app reads like a **hospital laboratory report**: a maroon letterhead on every page, report sections with heavy
rules, monospaced results with H/L flags and reference intervals, and the model's effect on the odds beside each
finding.

- **Screen a patient**: an intake form (or a held-out patient), the risk on a Routine / Check / Priority ruler next
  to the average patient and the patient's age group, **why** as a results table (each finding with its flag, reference interval and odds multiplier),
  what controlling hypertension or glucose would change, the next step, the FAST stroke warning signs and a
  downloadable summary.
- **Clinic list**: a triage board that sorts a list into three lanes, what each lane holds, and the full ranked list
  (select a row to open the patient); upload your own CSV.
- **Misses and false alarms**: move the screening line and see, on held-out patients, stroke patients found and
  missed, false alarms and a natural-frequency tree; every possible line on one curve; where the scores fall; and who
  the line misses.
- **Risk factors**: stroke rate by age with each condition, conditions and measurements, lifestyle and background,
  and a forest plot of what the model weighs once age is accounted for.
- **Model report**: how the model works, held-out results at both lines, ROC, calibration, the model search, data and limits.

## Why this stack

| Need | Choice |
|---|---|
| A clinician-facing tool: one patient in depth, a whole list in lanes, the cost of the screening line made visible | **Streamlit** with top navigation and session state for the list-to-patient flow |
| One artefact from raw record to risk, including patients without a BMI | **scikit-learn `Pipeline`** (k-nearest-neighbour BMI estimate, scaling, one-hot encoding, logistic regression), saved with `joblib` |
| Calibrated risks and exact, readable explanations | **Logistic regression**: tied with XGBoost and random forest in cross-validation (AUC-ROC about 0.84), and each score is the average patient's odds times one multiplier per factor |
| Reject bad uploads | **pydantic** schema per row (including "child" work type only under 18) |
| Trust that the shipped file is the evaluated model | **pytest** + GitHub Actions: scores, recall/AUC, explanation additivity, what-ifs, validation, every page |

`strokescope/` has no Streamlit dependency, so the same model can sit behind an API for a patient record system.

## How it is built

```
app.py              entry point (top navigation, logo)
nav.py              page registry
views/              screen, clinic_list, tradeoff, risk_factors, report
strokescope/        schema.py (pydantic), model.py (risk, tiers, explanations, what-ifs, odds ratios)
clinic/             laboratory-report UI kit (letterhead, report sections, results table with flags and reference
                    intervals, risk ruler, critical-alert box, worklist lanes), Plotly charts, theme
model/              stroke_risk_logreg.joblib + metadata.json
data/               held-out patients with outcome and score, all patients, reference statistics
train.py            rebuilds model/ and data/ from the CSV
tests/              model and page tests
```

## Run locally

```bash
pip install -r requirements-dev.txt
pytest -q
streamlit run app.py
python train.py "path/to/healthcare-dataset-stroke-data.csv"   # rebuild the model and data
```

## Data and limits

5,110 anonymised patient records from the public Kaggle stroke prediction dataset (origin not documented); 249
(4.9%) had a stroke. The data records past strokes at one point in time, so the model recognises stroke-like
profiles; it has not been shown to predict future strokes and has not been validated on another population.
StrokeScope is a portfolio demonstration, **not a medical device and not medical advice**. Anyone with stroke
symptoms (face drooping, arm weakness, speech difficulty) needs emergency care at once, whatever a score says.
