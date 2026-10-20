# Speech Health Screener

A Flask application that screens uploaded WAV recordings for acoustic patterns
associated with dysarthria. This is a screening aid, not a diagnosis, and does
not replace an assessment by a qualified clinician.

## Project layout

```text
.github/workflows/   CI checks
backend/src/         Flask API and shared backend code
backend/models/      Model, imputer, and scaler
backend/training/    Model evaluation and feature extraction tools
frontend/            HTML, CSS, and JavaScript served by Flask
requirements.txt     Python dependencies
render.yaml          Render deployment configuration
```

The frontend is plain HTML, CSS, and JavaScript; it has no separate Node build
step. Flask renders `frontend/index.html`, serves `frontend/assets/`, and
provides the `/predict` API.

## Run locally

From the repository root:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend/src/app.py
```

The app is available at `http://127.0.0.1:5000`. Copy `.env.example` to `.env` to configure the therapy tracker connection.
To securely save screening results to a patient account, configure the same
random `SCREENING_SHARED_SECRET` in both apps. The tracker should open the
screener with a short-lived signed patient token in the `token` query
parameter. Only the prediction and model score are sent to the tracker; audio
recordings are not.

## Tests

```powershell
python -m unittest discover -s backend/src/shared -p "test_*.py"
```

## Deploy

The `render.yaml` Blueprint installs `requirements.txt` and starts the
Flask app with Gunicorn. Configure `THERAPY_TRACKER_URL` and the same
`SCREENING_SHARED_SECRET` in both Render services to link the screener with the
tracker. Leave the secret unset to disable result transfer.

## Training

The scripts in `backend/training/` document the Kaggle evaluation and feature
extraction workflow. See [backend/training/README.md](backend/training/README.md)
for instructions. Dataset licenses, methodology, reported results, and the
model's validation limitations are in [backend/README.md](backend/README.md).
