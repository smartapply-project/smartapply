# Smart Application Processing — Outcome Checklist

## Applicant application and document intake

- [ ] Build a responsive applicant flow with fields for applicant name, email, date of birth, application type (Scholarship / Admission / Loan), marks percentage, and family income, plus required upload slots for ID proof, Marksheet, and Income certificate.
- [ ] Support drag-and-drop and file selection for PDF, JPG, and PNG uploads; show progress after each upload; return either a green verified card with the detected document type, confidence, and extracted fields or a red error card with a specific reason and a **Choose another file** action.
- [ ] If no document is uploaded, block processing and show exactly: `Application rejected: no documents were uploaded. Please upload the required documents.`
- [ ] If a required document is missing, list exactly which required documents are missing and do not proceed to approval.
- [ ] If a file is in the wrong slot or is irrelevant, a random image, a wrong document type, a blank page, an unreadable scan, corrupt, empty, oversized, or invalid by file signature/extension, reject it with a specific reason such as `This looks like a marksheet, not an income certificate.`

## Real backend document analysis pipeline

- [ ] Analyze the actual uploaded file on the backend for every upload; never simulate or hardcode analysis results, and never approve a document only because it is real or well formatted.
- [ ] Validate allowed types (PDF, JPG, PNG), size, byte length, emptiness, corruption, duplicate uploads, and parseability before analysis.
- [ ] Extract text from PDF documents using a PDF text extractor and use OCR or a vision-capable AI model for images and scans; keep any API key/secret server-side and never expose it to the browser.
- [ ] Classify the document type with a confidence score; reject a wrong-slot/irrelevant document with a specific reason.
- [ ] Extract name, DOB, marks/percentage, income, issue date, issuing authority, and ID numbers into structured JSON, with a confidence score for each field.
- [ ] Compare extracted values with the form and other documents; flag meaningful name mismatches while allowing minor spelling differences, DOB mismatch, percentage mismatch, income mismatch, expired or old documents including income certificates older than 12 months, missing signature or seal, and inconsistent values across documents.
- [ ] Give plain-language correction guidance for every issue, including guidance such as `You entered 88% but the marksheet shows 82%. Correct the form or upload the right marksheet.`
- [ ] Return Approved only when everything is consistent, Needs Correction for fixable issues, Manual Review for low confidence or uncertainty, and Rejected for missing documents or clear rule violations; always show the reasons.

## Application health, comparison, timeline, and resubmission

- [ ] Provide a live **Application health** meter that updates as documents are added and checked.
- [ ] Provide a side-by-side view of what the applicant typed versus what the documents contain, with mismatches highlighted.
- [ ] Provide a timeline showing each check and its result, including file checks, extraction, classification, field extraction, cross-checking, and decision.
- [ ] Provide a results page with the decision, every issue found, confidence signals, reasons, correction suggestions, and a **Fix and resubmit** flow that lets the applicant fix form fields and re-upload files, then rerun analysis.
- [ ] Handle blurry scans, rotated pages, multi-page PDFs, wrong file extensions, duplicate uploads, very large files, and network errors with recoverable states; route uncertain cases to Manual Review instead of guessing.

## Admin review dashboard

- [ ] Provide an admin dashboard listing all applications with status filters, search, health/decision badges, and timestamps.
- [ ] Let an admin open any application to view the submitted form, document metadata, extracted data with confidence, comparison results, reasoning, timeline, and correction history.
- [ ] Protect raw document access behind controlled application endpoints and do not log document contents.

## Privacy, persistence, and supporting documentation

- [ ] Persist applications, document metadata, extracted fields, confidence values, checks, issues, and resubmission history using the configured database; use local development storage only as a fallback and a durable project storage adapter for uploaded files.
- [ ] The app only analyzes and suggests corrections; it never edits or alters the uploaded document itself.
- [ ] Validate uploads, keep secrets server-only, avoid logging document contents, support deletion on request, and provide known limitations and privacy/retention boundaries.
- [ ] Deliver a README with setup steps, environment variables, local run commands, database setup, OCR/provider prerequisites, test commands, and production notes.
- [ ] Deliver an architecture diagram showing browser, FastAPI, validation/extraction/classification/cross-check/decision services, database, storage, and LLM provider.
- [ ] Deliver a test set containing a correct document, a document with a wrong name, a wrong document type, a blank file, and a no-upload case; document known limitations and disclose AI-assisted parts.

## Route, runtime, diagnostics, and delivery

- [ ] Serve `public/manus-routes.json` with HTTP 200 before the first server start and keep it synchronized with `/`, `/application/:id`, `/results/:id`, and `/admin`.
- [ ] Configure host-managed TypeScript, Python, JSON, HTML, and CSS diagnostics before the first application code batch and resolve actionable diagnostics.
- [ ] Run frontend typechecking/build and backend unit/API tests; verify the no-upload guard, required-document errors, specific wrong-slot reasons, extraction confidence, cross-check logic, correction suggestions, resubmission, manual-review fallback, admin views, and delete-on-request behavior.
- [ ] Set a quoted durable `logoUrl` literal in `app.config.ts` before checkpointing.
- [ ] Start the managed preview on port 3000, verify an HTTP health response, inspect responsive rendering, commit the completed project to the canonical `main` remote, and confirm the resulting checkpoint SHA; do not claim publication unless successful publication is separately confirmed.
