# Clearpath

**A practical resume-to-role skills analyzer.** Upload a resume, paste a job description, and get an evidence-backed view of skill overlap, priority gaps, and concrete ways to improve.

Clearpath is a portfolio project built with React, Vite, Python, and FastAPI. It is designed to help job seekers reflect on how their experience is presented. It does not assess a person's worth or predict an employer or applicant tracking system's decision.

## What it does

- Reads text-based PDF, DOCX, and TXT resumes (up to 10 MB).
- Uses a transparent skill vocabulary with curated synonyms.
- Shows the job-description phrase and resume phrase behind each direct match.
- Separates required and preferred skills. Required skills have twice the score weight of preferred skills.
- Optionally suggests related phrasing with a local sentence-transformer model. A related match receives half credit and is labeled for review.
- Provides a practical project task and a free learning link for each gap.
- Includes a synthetic one-click demo, report download, and a clear-analysis control.
- Processes resumes in memory for the request; Clearpath does not save resume files or analysis history.

## Quick start

Requires Python 3.10+ and Node.js 20+.

### 1. Start the API

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8001
```

### 2. Start the website

In a second terminal, from the project folder:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite. The Vite server forwards `/api` calls to FastAPI on port 8001. Use **Try a sample** to explore the full flow with fictional example data.

## Optional semantic matching

The default analyzer is fast, deterministic, and based on the editable skill/alias vocabulary. To enable optional related-phrase matching with a local sentence-transformer model, install the extra dependency and enable it before starting the API:

```powershell
python -m pip install -r requirements-semantic.txt
$env:CLEARPATH_SEMANTIC_MATCHING = "true"
python -m uvicorn api.main:app --reload --port 8001
```

The model (`sentence-transformers/all-MiniLM-L6-v2`) downloads on first use. Embedding and comparison run locally. Semantic matches are suggestions, receive half credit, and should be reviewed against the quoted resume evidence. Set `CLEARPATH_SEMANTIC_THRESHOLD` to adjust the similarity threshold; the default is `0.58`. See `.env.example` for configuration names. The optional model adds a larger dependency and initial download, so it is not part of the default setup.

## How the score works

1. Clearpath extracts selectable text from the uploaded file.
2. A curated list maps skill aliases and common synonyms to canonical skill names.
3. Required skills are weighted 2; preferred skills are weighted 1. Skills without an explicit preferred label default to required.
4. Direct phrase evidence earns full weight. If semantic matching is enabled, a related phrase above the configured threshold earns half weight and is labeled as related.
5. Weighted earned points divided by total recognized skill points gives the displayed percentage.

Only recognized skills contribute to this score. A missing phrase means Clearpath did not find evidence in the extracted text; it does not prove the candidate lacks that ability. Scanned PDFs that need OCR are not supported in this version.

## Verify locally

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm run build
npm run test:sites
```

The Python unit tests cover weighting, priority labels, evidence, redaction, synonyms, and empty-match behavior. The frontend build prepares the local preview and hosting artifacts; the Sites worker suite covers its static adapter.

## Project structure

```text
api/main.py              FastAPI upload, extraction, and matching API
src/App.jsx              React upload flow and evidence-backed report
src/styles.css           Responsive blue-glass design system
public/sample-resume.txt Fictional demo resume
samples/                 Synthetic fixtures
tests/                   Python analyzer and Sites worker checks
requirements-semantic.txt Optional local semantic-model dependency
```

## Privacy and production notes

There are no accounts or database. The server reads the uploaded file for the current request and does not persist it. The browser holds the selected file and result in page memory until the user clears the analysis or closes the page. API responses are marked `no-store`.

Before using a public deployment with real resumes, add a published privacy notice, request size and rate controls at the hosting layer, HTTPS, monitoring, and an explicit data-retention review. Never commit a real resume, credentials, `.env` file, or personal analysis output. Scanned-document OCR, wider skill coverage, and multilingual analysis are future improvements.

## Built with

React · Vite · FastAPI · pypdf · python-docx · optional sentence-transformers
