const input = document.getElementById('file-input');
const dropzone = document.getElementById('dropzone');
const fileDetails = document.getElementById('file-details');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const removeFileBtn = document.getElementById('remove-file');
const player = document.getElementById('player');
const analyzeBtn = document.getElementById('analyze');
const spinner = document.getElementById('spinner');
const result = document.getElementById('result');
const resultSymbol = document.getElementById('result-symbol');
const resultTitle = document.getElementById('result-title');
const resultText = document.getElementById('result-text');
const resultScore = document.getElementById('result-score');

const MAX_FILE_BYTES = 20 * 1024 * 1024;
let selectedFile = null;
let previewUrl = null;

function showResult(kind, title, message, score = '') {
  result.className = `result ${kind}`;
  resultTitle.textContent = title;
  resultText.textContent = message;
  resultScore.textContent = score;
  resultScore.hidden = !score;
  resultSymbol.textContent = kind === 'clear' ? '✓' : kind === 'flagged' ? '!' : '×';
  result.hidden = false;
  result.focus({ preventScroll: true });
}

function formatBytes(bytes) {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function clearPreview() {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  player.removeAttribute('src');
  player.load();
  player.hidden = true;
}

function clearFile() {
  selectedFile = null;
  input.value = '';
  clearPreview();
  fileDetails.hidden = true;
  analyzeBtn.disabled = true;
  result.hidden = true;
}

function setFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.wav')) {
    clearFile();
    showResult('error', 'Please choose a WAV file', 'This screener currently accepts .wav audio files.');
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    clearFile();
    showResult('error', 'This file is too large', 'Choose a WAV file that is 20 MB or smaller.');
    return;
  }
  if (file.size === 0) {
    clearFile();
    showResult('error', 'This file is empty', 'Choose a WAV recording that contains audio, then try again.');
    return;
  }

  selectedFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = `${formatBytes(file.size)} · WAV audio`;
  fileDetails.hidden = false;
  clearPreview();
  previewUrl = URL.createObjectURL(file);
  player.src = previewUrl;
  player.hidden = false;
  analyzeBtn.disabled = false;
  result.hidden = true;
}

input.addEventListener('change', () => setFile(input.files[0]));
removeFileBtn.addEventListener('click', clearFile);

['dragenter', 'dragover'].forEach(eventName => {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.add('dragover');
  });
});
['dragleave', 'drop'].forEach(eventName => {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.remove('dragover');
  });
});
dropzone.addEventListener('drop', event => setFile(event.dataTransfer.files[0]));
window.addEventListener('pagehide', clearPreview);

analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile || analyzeBtn.disabled) return;

  analyzeBtn.disabled = true;
  analyzeBtn.querySelector('span').textContent = 'Reviewing…';
  spinner.hidden = false;
  result.hidden = true;

  const form = new FormData();
  form.append('file', selectedFile);

  try {
    const response = await fetch('/predict', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The recording could not be processed. Please try again.');

    const modelScore = `Model score: ${data.confidence}%. This is not the likelihood of a condition.`;
    if (data.prediction === 1) {
      showResult(
        'flagged',
        'Patterns were detected',
        'The model found acoustic patterns associated with dysarthria in this recording. A qualified clinician can help interpret this result.',
        modelScore,
      );
    } else {
      showResult(
        'clear',
        'Patterns were not detected',
        'The model did not detect notable patterns in this recording. This does not rule out dysarthria or replace an assessment by a qualified clinician.',
        modelScore,
      );
    }
  } catch (error) {
    showResult('error', 'We couldn’t review this recording', error.message || 'Please check the WAV file and try again.');
  } finally {
    spinner.hidden = true;
    analyzeBtn.disabled = !selectedFile;
    analyzeBtn.querySelector('span').textContent = 'Review speech patterns';
  }
});
