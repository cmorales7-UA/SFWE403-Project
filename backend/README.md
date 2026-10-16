# UA-GDAS backend: stories 9.2.1, 9.2.2, 9.2.4, 9.2.5

This delivery adds only the `backend/` folder. Every original project file,
including the frontend, root requirements and main.py, is unchanged.

## Structure

| Folder | Responsibility |
| --- | --- |
| models | Request schemas and field validation |
| clients | SQLite connection and persistence operations |
| service | Account, session, program, and authorization rules |
| routes | FastAPI endpoints, cookies, and request handling |

Tests, an independent launcher, setup instructions, and a local administrator
bootstrap are also included inside backend.

## Run (Python 3.10+)

From the project root, create and activate a virtual environment:

Windows Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Then on either platform:

```sh
python -m pip install -r backend/requirements.txt
python -m backend.bootstrap
python -m uvicorn backend.app:app --reload --port 8001
```

Open http://127.0.0.1:8001/docs to test the API. The bootstrap command prompts
for a local administrator; no default credentials are shipped. Database files
are created automatically under backend/data/ and persist after restart.
Set GDAS_DB_PATH to override the location. Database data is excluded from Git.

## Manual acceptance test

1. In /docs, expand POST /api/users, select Try it out, and supply all fields.
   An example request is shown below. Expect 201 and user_type applicant.
   Password and answer hashes never appear in responses. Reusing a username or
   email returns 409; adding user_type to registration returns 422.
2. POST /api/login using the administrator credentials from bootstrap. The
   browser stores the HttpOnly session cookie; subsequent /docs requests use it.
3. GET /api/users; note the applicant id. PATCH /api/users/{user_id} with
   {"first_name":"Updated","user_type":"reviewer"}. Expect saved changes.
4. POST /api/programs with the full example below. Note the returned id.
5. GET /api/programs and GET /api/programs/{program_id}. Verify saved fields.
6. PUT /api/programs/{program_id} with the complete program object, changing
   degree_requirements. Retrieve it again and restart the server to confirm
   persistence. PUT replaces all program fields; send the full object.
7. POST /api/logout, then GET /api/users. Expect 401. Log in as the ordinary
   applicant and attempt GET /api/users or a program write: expect 403.
8. As administrator, change a test account to it_support and log in as it.
   Account detail updates succeed, but assigning another user type returns 403.
   An advisor can retrieve and update programs; applicant/reviewer/reference/IT
   accounts cannot manage programs.

Registration example (replace sample details as desired):

```json
{
  "username": "student1", "password": "ExamplePassword123!",
  "security_question_1": "First pet?", "security_answer_1": "Example",
  "security_question_2": "First school?", "security_answer_2": "Example",
  "first_name": "Test", "last_name": "Student", "net_id": "",
  "phone": "5551234567", "email": "student1@example.com"
}
```

Program example:

```json
{
  "degree_name": "Software Engineering", "degree_level": "masters",
  "degree_college": "Engineering", "degree_description": "Graduate program",
  "campus_offered": ["main", "online"], "terms_offered": ["Fall 2027"],
  "degree_requirements": "Bachelor degree", "application_deadline": "2027-01-15",
  "application_fee": "90.00", "sponsor_question": "Sponsor name and contact?",
  "ta_ra_question": "Interested in assistantships?", "funding_question": "Funding?",
  "english_test_question": "English test, if applicable?",
  "english_score_question": "English score, if applicable?",
  "other_requirements": "Resume", "program_contact": "grad@example.com"
}
```

## Automated tests

```sh
python -m pytest backend/tests tests -q
```

Tests use isolated temporary SQLite files. They cover persistence, every account
and program field, secret hashing, default roles, duplicate accounts, validation,
administrator/IT/advisor permissions, program updates and session revocation.
Original frontend tests are retained. No browser/form integration is claimed.

## Frontend handoff

The frontend is intentionally unchanged and is not yet connected. Its owner can
include `backend.routes.api.router` in the existing FastAPI app (same origin) when
ready; a separate backend app is provided for independent testing. No CORS policy
is enabled for cross-origin frontend requests. Do not use browser local storage
to hold passwords or invent authentication headers based on a user id.

Endpoints, all with JSON request bodies:

| Method | Endpoint | Access |
| --- | --- | --- |
| POST | /api/users | Public; always creates applicant |
| POST | /api/login | Public; returns session cookie |
| POST | /api/logout | Revokes current session |
| GET | /api/users | Administrator / IT support |
| PATCH | /api/users/{id} | Administrator / IT; role changes admin only |
| POST | /api/programs | Administrator / advisor |
| GET | /api/programs | Administrator / advisor |
| GET | /api/programs/{id} | Administrator / advisor |
| PUT | /api/programs/{id} | Administrator / advisor |

The account form currently calls phone/email phone_number/email_address. Map
these to phone/email when sending JSON. Roles use applicant, administrator,
advisor, reviewer, reference, it_support. Password and security answers are
salted scrypt hashes; responses exclude these hashes. NetID is optional.

9.2.1 explicitly restricts assigning other user types to administrators, while
9.2.2 uses the broader term authorized users. This implementation follows the
explicit restriction; confirm this interpretation with the team.

## Scope

Implemented: the four backend stories named above, plus supporting session
authentication. Not implemented: other application/recommendation-letter
stories, password recovery, or frontend integration. Before public deployment,
add login abuse throttling and deployment-specific security settings. Use HTTPS;
the session cookie is Secure when the request uses HTTPS.
