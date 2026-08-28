# ResumeFit AI

ResumeFit AI is a full-stack resume tailoring application. Phases 1–8 cover Firebase authentication, private S3 uploads, structured resume parsing, job analysis, deterministic matching, safe AI-assisted optimization, and final ATS-readable PDF generation. Database persistence and resume history remain intentionally deferred.

## Repository layout

```text
frontend/   React, Vite, Tailwind CSS, React Router, React-PDF, Axios, Firebase Auth
backend/    FastAPI, Pydantic, Firebase Admin, boto3, Jinja2, WeasyPrint/ReportLab
```

Workflow state remains in React for the active session; no fake database persistence is used.

## Prerequisites

- Node.js 18 or newer
- Python 3.11 or newer

## Frontend setup

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

The frontend is available at `http://localhost:5173` by default.

## Backend setup

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

## Firebase Authentication setup (Phase 2)

### 1. Create and configure a Firebase project

1. Open the [Firebase console](https://console.firebase.google.com/) and create or select a project.
2. Go to **Build → Authentication → Sign-in method**.
3. Enable the **Email/Password** provider.
4. In **Project settings → General**, add a Web App if one does not exist.
5. Copy the Web App configuration values shown by Firebase. These values identify the Firebase project; do not place an Admin private key in the frontend.

### 2. Configure the frontend

Create `frontend/.env` from `frontend/.env.example`, then populate the Web App values:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_FIREBASE_API_KEY=your_web_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
```

Only use the Firebase Web App configuration here. Never place service-account credentials or private keys in the frontend.

### 3. Configure Firebase Admin for the backend

1. In Firebase, open **Project settings → Service accounts**.
2. Select **Generate new private key** and download the JSON file.
3. Create `backend/secrets/` locally.
4. Place the downloaded file at `backend/secrets/firebase-service-account.json`.
5. Create `backend/.env` from `backend/.env.example` and set:

```dotenv
FRONTEND_URL=http://127.0.0.1:5173
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=secrets/firebase-service-account.json
```

The secrets directory and the conventional service-account filename are ignored by Git. Do not commit or share the downloaded JSON file.

### 4. Install dependencies and run both servers

Backend terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # skip if already configured
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env  # skip if already configured
npm run dev -- --host 127.0.0.1
```

### 5. Manual authentication test

1. Open `http://127.0.0.1:5173/register`.
2. Register with a name, email, and password of at least six characters.
3. Confirm that registration redirects to `/dashboard`.
4. Refresh the dashboard and confirm the session remains active.
5. Select **Test Protected API** and confirm the API displays the Firebase UID and email.
6. Select **Logout** and confirm the app returns to `/login`.
7. Navigate directly to `/dashboard` and confirm it redirects to `/login`.

## AWS S3 upload setup (Phase 3)

### 1. Create a private development bucket

1. In the AWS S3 console, create a bucket in the region you intend to use.
2. Keep **Block Public Access** enabled for the bucket.
3. Do not add a public bucket policy or public object ACL.
4. Record the exact bucket name and AWS region.

ResumeFit AI writes originals to this private key pattern:

```text
users/{firebase_uid}/resumes/{resume_id}/original.pdf
```

The API never accepts a user ID from the browser and never returns a public S3 URL.

### 2. Create narrowly scoped development credentials

Create a dedicated IAM identity for local development. Do not attach `AdministratorAccess`. A practical minimum policy for the configured bucket is:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/users/*"
    }
  ]
}
```

Phase 3 upload uses only `s3:PutObject`. `GetObject` and `DeleteObject` support the already-defined S3 service operations intended for later authorized routes. No bucket-listing or bucket-metadata permission is required by this implementation.

For deployed environments, prefer an attached IAM role with equivalent permissions over long-lived access keys. Phase 3 local development uses the explicit environment values requested by the project specification.

### 3. Configure the backend environment

Add these values to `backend/.env`:

```dotenv
AWS_ACCESS_KEY_ID=your_development_access_key
AWS_SECRET_ACCESS_KEY=your_development_secret
AWS_REGION=ap-south-1
AWS_S3_BUCKET=resumefit-ai-dev
```

Never put these values in `frontend/.env`, source files, screenshots, or commits.

### 4. Manual private upload test

1. Complete the Firebase configuration from Phase 2.
2. Configure the four AWS variables above.
3. Start FastAPI and the React development server.
4. Register or log in and open `/dashboard`.
5. Select a PDF smaller than or equal to 5 MB.
6. Select **Upload Resume** and confirm the resume ID and uploaded status appear.
7. Open the S3 console and verify `users/{firebase_uid}/resumes/{resume_id}/original.pdf` exists.
8. Inspect the object permissions and confirm the object is not public.

The protected endpoint is `POST /api/resumes/upload` using multipart field `file`.

## Mistral resume parsing setup (Phase 4)

Phase 4 downloads the authenticated user's private PDF from S3, extracts selectable
text with PyMuPDF, and sends only that text to Mistral for schema-constrained resume
extraction. The response is returned to the current browser session and is not yet
stored in a database.

1. Create an API key in the Mistral developer console.
2. Add the following values to `backend/.env`:

```dotenv
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-small-latest
```

3. Install the updated backend dependencies and restart FastAPI.
4. Upload a PDF, then select **Parse Resume**.

The protected endpoint is `POST /api/resumes/{resume_id}/parse`. It derives the S3
object key from the verified Firebase UID, never accepts another user's UID, and
does not return raw extracted text. PDFs must contain at least 50 visible selectable
characters; password-protected, corrupt, image-only/scanned, and overlong extracted
documents are rejected. OCR is not included in this phase.

Never put the Mistral key in `frontend/.env`, client-side code, screenshots, or Git.

## Job description analysis (Phase 5)

After a resume is parsed, the dashboard displays a **Tailor for a Job** form.
Enter the company name, job role, and a meaningful job description between 100
and 30,000 characters, then select **Analyze Job**. The protected backend sends
only the job details to Mistral and validates the structured response before
rendering required and preferred skills, responsibilities, technologies,
experience, education, and meaningful keywords.

The endpoint is:

```text
POST /api/jobs/analyze
```

Example request body:

```json
{
  "resume_id": "a-valid-resume-uuid",
  "company": "Example Corp",
  "role": "Software Engineer",
  "job_description": "The complete job posting text..."
}
```

The `resume_id` is included only for future workflow continuity. Phase 5 does
not download or send the resume, compare the candidate with the job, calculate
an ATS score, or persist the analysis. Each response includes a temporary
`job_id`; it will not survive as stored application data until persistence is
added in a later phase.

Job analysis uses the same `MISTRAL_API_KEY` and configurable `MISTRAL_MODEL`
documented above. To test manually:

1. Log in and upload a selectable-text PDF.
2. Parse the resume successfully.
3. Enter the company and role, then paste a real job description.
4. Select **Analyze Job** and compare the structured required/preferred fields
   with the original posting.
5. Confirm that no match percentage or resume comparison appears.

## Resume matching and estimated ATS score (Phase 6)

After job analysis, select **Calculate Resume Match**. The frontend temporarily
sends the already parsed `resume` and analyzed `job` objects with their workflow
IDs to the protected endpoint:

```text
POST /api/match/analyze
```

This temporary request shape is necessary because MongoDB persistence has not
been introduced yet. The deterministic matcher performs no AWS or Mistral calls
and uses fixed category weights:

| Category | Weight |
| --- | ---: |
| Skills | 40% |
| Experience | 25% |
| Projects | 15% |
| Keywords | 10% |
| Education | 5% |
| Resume completeness | 5% |

Categories the job does not specify, such as education or important keywords,
are marked not applicable and excluded from the final normalization. Required
skills receive more weight than preferred skills. Matching is case-insensitive,
uses a small explicit technology alias map, and avoids substring matches such as
Java/JavaScript or C/CSS.

The **ResumeFit Match Score** is an estimated compatibility score based only on
the job requirements and information present in the uploaded resume. It does not
represent the private scoring system of any specific employer or ATS. A missing
skill means only that it was not found in the uploaded resume; ResumeFit never
inserts missing skills automatically.

To test manually, complete the upload, resume parsing, and job-analysis flow,
then select **Calculate Resume Match**. Verify the score, applicable breakdown,
matched and missing skills, keywords, relevant experience/projects, strengths,
and factual gaps. Repeating the request with identical structured inputs should
produce the identical result.

## AI-assisted resume optimization (Phase 7)

After calculating a match, select **Optimize Resume** to run the controlled
optimization pipeline:

```text
Original Resume + Job Analysis + Match
→ Mistral Suggestions
→ Deterministic Safety Validation
→ Accept / Reject / Edit
→ Server-side Apply
→ Deterministic Match Recalculation
```

The protected endpoints are:

```text
POST /api/optimizations/generate
POST /api/optimizations/apply
```

Generation returns a maximum of 12 individually reviewable summary, experience
bullet, or project bullet rewrites. Suggestion IDs and original target text are
set by the backend rather than trusted from the model. Unsafe suggestions are
dropped independently, so one unsafe response does not invalidate every safe
rewrite.

Every generated or user-edited change is validated against the original
structured resume before application. Validation checks the exact target,
evidence quoted from the resume, known technology additions, new numerical
claims, and high-risk responsibility/impact verbs. Missing job skills are never
inserted merely because the job requests them. Accepted and edited changes are
applied to a deep copy; rejected and pending suggestions leave the original
content unchanged.

The optimized structured preview shows the actual deterministic match score
before and after approved changes. The after score is not forced to improve.
Phase 7 does not persist suggestions or optimized data. Phase 8 consumes its
validated `optimized_resume` object to generate the final PDF.

Manual workflow:

1. Complete resume parsing, job analysis, and resume matching.
2. Select **Optimize Resume**.
3. Accept, reject, and edit individual suggestions.
4. Select **Apply Approved Changes**.
5. Confirm rejected content remains unchanged and unsupported edits are blocked.
6. Review the structured optimized preview and before/after score.

## Final ATS resume PDF (Phase 8)

After approved changes are applied, select **Generate Final Resume**. The
protected backend validates the current `ResumeSchema`, renders the trusted
`ats_standard` Jinja2 HTML/CSS template, and uses WeasyPrint when its native
libraries are available. If WeasyPrint cannot load its platform libraries, the
same structured resume is rendered by the built-in ReportLab fallback. Both
paths produce a real text PDF rather than an image or browser screenshot.

The protected endpoints are:

```text
POST /api/optimizations/{optimization_id}/generate-pdf
POST /api/optimizations/pdf-access
```

The generation request carries the temporary workflow IDs, company, role, and
optimized resume because MongoDB is not available yet. The access endpoint only
refreshes signed URLs; it does not regenerate the object. Both request schemas
forbid extra fields such as `uid`, `user_id`, and `s3_key`. The server always
constructs the key from the verified Firebase UID:

```text
users/{uid}/resumes/{resume_id}/jobs/{job_id}/optimizations/{optimization_id}/optimized.pdf
```

The original `users/{uid}/resumes/{resume_id}/original.pdf` is never modified.
Generated objects are uploaded without a public ACL and with
`Content-Type: application/pdf`. Separate S3 `get_object` URLs are signed for
inline preview and attachment download. They expire after 900 seconds. Download
filenames are generated from sanitized candidate/company/role values and never
become part of the S3 key.

The React-PDF preview uses the bundled PDF.js worker and renders every page with
its selectable text layer. A dedicated **Refresh Link** action renews expired
preview/download URLs without creating another PDF. **Regenerate** writes the
latest approved resume to the same temporary optimization path.

### S3 CORS for browser preview

React-PDF fetches the signed S3 URL in the browser, so the private bucket must
allow `GET` and `HEAD` from the local frontend origin. In S3 **Permissions →
Cross-origin resource sharing (CORS)**, use a narrowly scoped development rule:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["http://127.0.0.1:5173", "http://localhost:5173"],
    "ExposeHeaders": ["Content-Length", "Content-Range", "Accept-Ranges"]
  }
]
```

Replace these origins with the exact deployed frontend origin in production;
do not use a wildcard origin for the authenticated application.

### WeasyPrint on Windows

`pip install -r requirements.txt` installs the Python package, but WeasyPrint
also needs native Pango/GLib libraries. On Windows, follow the official
[WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation),
typically using WSL or installing the required libraries with MSYS2 and making
their DLL directory discoverable. A missing `libgobject-2.0-0` means these
native libraries are not available. This project automatically uses ReportLab
in that case, so local PDF generation remains functional and ATS-readable.

### Manual Phase 8 check

1. Complete login, upload, parsing, job analysis, matching, and optimization.
2. Accept/reject/edit suggestions, then apply approved changes.
3. Select **Generate Final Resume** and scroll through every preview page.
4. Download the dedicated attachment URL and open the file.
5. Confirm text can be selected and searched, facts remain accurate, and no
   unsupported skills were added.
6. In S3, confirm `optimized.pdf` is private under the optimization path and the
   original PDF still exists unchanged.

## MongoDB persistence and history (Phase 9)

Phase 9 makes MongoDB the authoritative source for application state. Firebase
continues to own authentication and passwords, S3 stores the original and
optimized PDF binaries, Mistral performs structured parsing/analysis, and
MongoDB stores metadata plus structured workflow data. PDFs are intentionally
not stored in MongoDB because S3 is designed for private binary object storage
and short-lived signed access.

Collections and responsibilities:

- `users`: Firebase UID, email, and timestamps. Protected requests upsert this
  record automatically.
- `resumes`: private S3 metadata, upload status, and parsed `ResumeSchema`.
- `jobs`: job description, structured analysis, deterministic match, and status.
- `optimizations`: immutable suggestion targets, user decisions, optimized
  resume, before/after match, and generated PDF metadata.

All reads, writes, and deletes use both the application UUID and authenticated
Firebase UID. Raw MongoDB `_id` values and private S3 keys are not returned in
public detail/history responses. Repository modules under
`backend/app/repositories/` contain database queries; routes orchestrate
validation, services, compensation, and safe error responses.

### MongoDB Atlas setup

1. Create an Atlas project and cluster.
2. Create a least-privilege database user and save its password securely.
3. Under **Network Access**, allow only the development machine or deployment
   network. Avoid permanent `0.0.0.0/0` access.
4. Copy the driver connection URI and URL-encode special password characters.
5. Set these values in `backend/.env`—never in the frontend:

```dotenv
MONGODB_URI=mongodb+srv://database-user:password@cluster.example.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=resume_fit_ai
```

6. Restart FastAPI. Startup pings MongoDB and creates unique UUID/UID indexes,
   owner indexes, relation indexes, and owner/creation-time compound indexes.

If configuration or connectivity is unavailable, persistent endpoints return
`503` with a safe message. Tests use an isolated in-memory Mongo-compatible
database and never require Atlas.

### Persistent APIs

```text
GET    /api/resumes
GET    /api/resumes/{resume_id}
DELETE /api/resumes/{resume_id}
GET    /api/jobs?resume_id=...
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/match
DELETE /api/jobs/{job_id}
POST   /api/optimizations/generate
GET    /api/optimizations/{optimization_id}
PATCH  /api/optimizations/{optimization_id}/apply
POST   /api/optimizations/{optimization_id}/generate-pdf
GET    /api/optimizations/{optimization_id}/pdf-access
DELETE /api/optimizations/{optimization_id}
GET    /api/dashboard/history
```

The legacy `POST /api/match/analyze` remains temporarily for Phase 6 client
compatibility, but the current frontend uses the persisted job match endpoint.
Dashboard, resume detail, job detail, and optimization routes reload their data
from FastAPI after a browser refresh; full workflow objects are not stored in
local storage.

Resume deletion uses a controlled owner-only cascade: original S3 PDF,
generated PDFs, optimizations, jobs, then the resume record. The UI requires a
custom confirmation modal. MongoDB transactions are not required; S3/MongoDB
cross-system failures use best-effort compensation and server logging.

## Automated verification

With the backend running:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Run the automated checks:

```powershell
cd backend
pytest
python -m compileall -q app

cd ..\frontend
npm run build
npm run lint
```

## Environment configuration

Copy each `.env.example` file to `.env`. Never commit the resulting `.env` files or real credentials. Phase 4 reads Firebase, AWS, Mistral, and frontend/API URL values. MongoDB remains reserved for a later phase.
