# UA-GDAS Backend and Program Management

UA-GDAS uses FastAPI, server-rendered Jinja templates, browser-side JavaScript, and SQLite. Account changes, graduate program records, application statuses, review assignments, and recommendations are persisted in SQLite.

## Running locally

From the project root, install dependencies:

```powershell
python -m pip install -r requirements.txt
```

On Windows, launch `run.bat`. This starts the application with its persistent database at `backend/data/gdas.sqlite3`. The first run imports existing local data if available; otherwise it initializes illustrative accounts and applications. Restarting does not repopulate or reset stored records.

The original database file is retained as a fallback during migration. Existing account passwords, application IDs, reviews, and user edits remain unchanged. A previously configured account keeps its existing password.

Initial illustrative accounts have full names, first.last usernames, and `@arizona.edu`-formatted email addresses. They are **fictional local test records**, not verified University of Arizona accounts or email inboxes. Keep outbound email routed only to the local SMTP testing server. The initial account password is generated when a new database is first initialized and printed in that local terminal. You may instead supply `GDAS_STARTER_PASSWORD` before initialization. Do not use sample accounts or local-only credentials in production.

For a clean deployment, create administrator credentials interactively with `python -m backend.bootstrap` and avoid loading illustrative records.

## SRS 9.5.1: Collaborative Graduate Degree Program Management

The existing Create and Modify Degree Program pages use the authenticated database API.

- Administrators may create and update any graduate degree program.
- Administrators may select registered advisors who can maintain a program.
- An assigned or collaborating advisor may update the relevant program, and an advisor may create a new program they can subsequently maintain.
- The program record stores degree name, degree level, administering college, description, general requirements, supplementary application questions, campus options, application terms, deadline, application fee, Arizona resident tuition per unit, non-resident tuition per unit, and contact information.
- Every creation or material update is recorded in `program_change_history` with the user who made the change, their role, timestamp, and modified field names.
- Previously saved program records with unknown tuition rates remain valid but display those rates as not provided until entered by an administrator or authorized advisor. New program creation requires both rates and at least one term.

Available endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/programs` | List programs visible to the current administrator or advisor |
| POST | `/api/programs` | Create a program |
| GET | `/api/programs/{id}` | Retrieve an authorized program |
| PUT | `/api/programs/{id}` | Update an authorized program |
| GET | `/api/programs/{id}/history` | View authorized program change history |


## SRS 9.6: Application reporting and analytics

Administrators can open /administrator/reports. Advisors can open
/advisor/reports and see only applications in their assigned degree programs.
Both dashboards use persisted application data and allow selecting a program,
term, campus, application status, and decision.

The report types implement:
- 9.6.1: current submitted graduate applications with detailed application
  information, supplemental answers, and downloadable CSV.
- 9.6.2: tailored reports with custom filters and selectable output columns.
- 9.6.3: recommended/accepted or intent-to-matriculate applications.
- 9.6.4: denied or deferred applications.
- 9.6.5: pending or in-review applications.
- 9.6.6: bar-chart comparisons by degree program, ethnicity, country of legal
  residence, applicant-reported gender, campus, prior degree type, prior UA
  degree, term, or application status. Charts can export aggregate CSV counts.

CSV exports protect formula-like applicant values, and report pages are marked
Cache-Control: no-store. Missing information is displayed as "Not provided"
on pages and left blank in CSV; a field is not invented when the application
has not stored it. Test with fictional applicant records.

## Testing

```powershell
python -m pytest backend/tests tests/frontend -q
```

Tests use temporary SQLite databases and do not intentionally change `gdas.sqlite3`.

## Deployment and privacy considerations

This is a course project, not an official deployed admissions service. Do not represent illustrative records as verified university identities. Before handling real applicants or connecting to university mail, deploy with approved authentication, HTTPS, restricted data access, security logging, backups, and appropriate privacy/security review. Tuition fields must be populated with current approved rates; no real tuition rates are implied by local sample data.
