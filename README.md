# SmartApply

**Evidence-led application document processing and review workspace.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-open%20SmartApply-6d5dfc)](https://smartapply-1-cfix.onrender.com/)

> **Live Demo:** [Open SmartApply](https://smartapply-1-cfix.onrender.com/)

## What it does

SmartApply helps process scholarship, admission, and loan applications by:

- Validating uploaded PDF, JPG, JPEG, and PNG files
- Classifying documents as Government ID, Marksheet, or Income Certificate
- Extracting names, dates, marks, income, identifiers, issue dates, and authorities
- Reporting realistic, evidence-based confidence scores
- Comparing extracted evidence with application-form values and other documents
- Routing unreadable or uncertain evidence to **Manual Review** instead of guessing
- Providing an applicant workspace and an admin review desk

## Why it matters

SmartApply is designed around one principle: **do not guess when evidence is unclear**. Clear documents can be processed automatically; mismatches and unreadable scans are surfaced with a reason and a next step for correction or human review.

## How the workflow works

1. The applicant creates an application with name, DOB, application type, marks, and family income.
2. The applicant uploads the three required evidence files.
3. The backend validates file type, signature, size, and content.
4. PDF text is extracted with `pypdf`; image scans use Tesseract OCR, with optional server-side vision assistance.
5. The analysis engine classifies the document and extracts structured fields.
6. Confidence-aware checks compare the evidence with the form and other documents.
7. The application becomes **Approved**, **Needs Correction**, **Rejected**, or **Manual Review**.

## Technology stack

- **Frontend:** React, TypeScript, Vite, Lucide icons
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Document processing:** pypdf, Tesseract OCR, optional OpenAI-compatible vision endpoint
- **Storage:** SQLite locally; configurable `DATABASE_URL` for deployment
- **Packaging:** Docker, pnpm, pytest
- **Repository:** GitHub — [smartapply-project/smartapply](https://github.com/smartapply-project/smartapply)

## Test the live demo

Use these synthetic demo values:

| Field | Value |
|---|---|
| Applicant name | Ravi Kumar Sample |
| Email | ravi.demo@example.com |
| Date of birth | 2004-08-15 |
| Application type | Scholarship |
| Marks percentage | 87.2% |
| Family income | 180000 |

Upload the clear sample files from `demo-samples/`:

- `government-id.pdf`
- `marksheet.pdf`
- `income-certificate.pdf`

Expected result:

- ID: **Verified**, approximately **94% confidence**
- Marksheet: **Verified**, approximately **88% confidence**
- Income Certificate: **Verified**, approximately **94% confidence**
- Final decision: **Approved** with consistent cross-document evidence

To demonstrate the human-in-the-loop path, replace the ID with `demo-samples/unreadable-id.pdf`. The expected result is **Manual Review**, with a clear explanation that the document could not be read and should be replaced or checked by a reviewer.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
corepack enable
pnpm --dir frontend install
pnpm --dir frontend build
uvicorn backend.app.main:app --host 0.0.0.0 --port 3000
```

Open `http://localhost:3000`.

## Test and build

```bash
pytest -q backend/tests
pnpm --dir frontend typecheck
pnpm --dir frontend build
```

## Routes

- `/` — applicant form and workspace creation
- `/application/:id` — upload, health, timeline, and evidence review
- `/results/:id` — decision, issue explanations, comparisons, and resubmission
- `/admin` — review queue and manual-review desk
- `/health` — unauthenticated runtime health endpoint

## GitHub release information

- Repository: [github.com/smartapply-project/smartapply](https://github.com/smartapply-project/smartapply)
- Branch: `main`
- Release package: `smartapply-final.zip`
- The release package contains the same application source committed to `main`, plus synthetic demo samples for judges.

## Privacy and limitations

The included documents are fictional test fixtures and are not official government records. SmartApply provides analysis and correction suggestions; it does not replace an official human or institutional review. Before production use, add role enforcement for the admin route and configure durable production storage/database services.
