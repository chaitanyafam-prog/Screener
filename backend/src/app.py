import os
import tempfile
import warnings
from pathlib import Path

import joblib
import librosa
import numpy as np
import parselmouth
from flask import Flask, jsonify, render_template, request
from parselmouth.praat import call

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_DIR / 'frontend'
MODEL_DIR = BACKEND_DIR / 'models'


def _load_project_env():
    env_path = PROJECT_DIR / '.env'
    try:
        with env_path.open(encoding='utf-8') as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    except OSError:
        pass


_load_project_env()

warnings.filterwarnings('ignore')

if __package__:
    from .shared.linking import post_screening, read_token, secret
else:
    from shared.linking import post_screening, read_token, secret

app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR),
    static_folder=str(FRONTEND_DIR / 'assets'),
    static_url_path='/assets',
)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB upload cap
_proxies = int(os.environ.get('TRUSTED_PROXIES', '0') or 0)
if _proxies:   # behind a hosting proxy, so request.remote_addr is the visitor and not the proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_proxies, x_proto=_proxies, x_host=_proxies)

model = joblib.load(MODEL_DIR / 'svm_final_combined.pkl')
imputer = joblib.load(MODEL_DIR / 'imputer_final.pkl')
scaler = joblib.load(MODEL_DIR / 'scaler_final.pkl')


def extract_rich_features(path, sr=16000):
    y, sr = librosa.load(path, sr=sr)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    delta = librosa.feature.delta(mfcc)
    delta2 = librosa.feature.delta(mfcc, order=2)
    mfcc_feats = np.concatenate([
        mfcc.mean(axis=1), mfcc.std(axis=1),
        delta.mean(axis=1), delta.std(axis=1),
        delta2.mean(axis=1), delta2.std(axis=1)
    ])

    zcr = librosa.feature.zero_crossing_rate(y).mean()
    rmse = librosa.feature.rms(y=y).mean()

    snd = parselmouth.Sound(path)
    point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)

    try:
        jitter = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    except Exception:
        jitter = 0
    try:
        shimmer = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    except Exception:
        shimmer = 0
    try:
        harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)
    except Exception:
        hnr = 0
    try:
        formant = call(snd, "To Formant (burg)", 0.0025, 5, 5500, 0.025, 50)
        f1 = call(formant, "Get mean", 1, 0, 0, "Hertz")
        f2 = call(formant, "Get mean", 2, 0, 0, "Hertz")
    except Exception:
        f1, f2 = 0, 0

    clinical_feats = np.array([jitter, shimmer, hnr, f1, f2, zcr, rmse])
    return np.concatenate([mfcc_feats, clinical_feats])


def _tracker_url():
    url = os.environ.get('THERAPY_TRACKER_URL', '').strip().rstrip('/')
    if not url and request.host.split(':', 1)[0].lower() in {'localhost', '127.0.0.1'}:
        url = 'http://localhost:5001'
    return url or None


@app.route('/')
def index():
    tracker_url = _tracker_url() or ''
    return render_template('index.html', tracker_url=tracker_url or None)


@app.route('/predict', methods=['POST'])
def predict():
    file = request.files.get('file')
    if file is None or file.filename == '':
        return jsonify(error='No file uploaded.'), 400
    if not file.filename.lower().endswith('.wav'):
        return jsonify(error='Please upload a .wav file.'), 400

    # Per-request temp file so concurrent users never overwrite each other.
    fd, tmp_path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        file.save(tmp_path)
        feat = extract_rich_features(tmp_path).reshape(1, -1)
        feat = scaler.transform(imputer.transform(feat))

        pred = int(model.predict(feat)[0])
        prob = model.predict_proba(feat)[0]
        confidence = round(float(prob[pred]) * 100, 1)
        token = request.form.get('token', '').strip()
        tracker_status = 'not_linked'
        if token:
            key = secret()
            if not key:
                tracker_status = 'unavailable'
            elif read_token(token, key) is not None:
                tracker_status = (
                    'saved'
                    if post_screening(_tracker_url(), token, pred, confidence, key)
                    else 'failed'
                )
            else:
                tracker_status = 'invalid_link'
        return jsonify(
            prediction=pred,
            confidence=confidence,
            tracker_status=tracker_status,
        )
    except Exception as e:
        return jsonify(error=f'Could not process this file: {e}'), 422
    finally:
        os.remove(tmp_path)


if __name__ == '__main__':
    app.run(debug=True)
