# Admissions Processing: ConOps Verification and Test Plan

**Scope:** SRS 9.5.2, 9.5.3, 9.5.4, 9.5.5  
**Source:** UA-GDAS System ConOps and Requirements, Sections 7.5, 8.6, 8.8, 9.4.5, 9.5.2–9.5.5 (pages 10, 14, 25–27).  
**Environment:** Local FastAPI + SQLite + local SMTP capture; no real UA Registrar integration.

## Architecture and decision flow

Graduate Program Advisor saves **Recommend / Deny / Defer** and emails their saved decision to a selected Graduate College Administrator (SRS 9.4.5). Graduate College Administrator can issue a formal **Accepted / Denied** email and printable hard-copy letter only after receipt of a final Recommend / Deny decision. Defer is not an official admission decision.

For an accepted application, two separate downstream requirements exist:

1. **SRS 9.5.5**: Administrator creates an admitted-graduate-student record after confirming required ConOps applicant fields and a verified official transcript. This is **not conditional on a matriculation intent**. Applicant-supplied tuition eligibility is retained; administrator-selected residency classification determines the approved per-unit tuition rate.
2. **SRS 9.5.3–9.5.4**: Applicant notifies Graduate College of acceptance through their authenticated portal; the Administrator processes the received intent, updating the status to **Intent to Matriculate** and saving a local-only Registrar notification containing the academic term. This can happen before or after the accepted-student record exists.

Data is persisted in SQLite tables named `official_admission_notices`, `admission_intents`, `official_transcripts`, `admitted_graduate_students`, and `registrar_simulations`. Existing application and account IDs are reused. Private transcript files are stored outside public static content.

## Requirements traceability

| SRS | Behavior | Implementation | Automated tests | Manual verification |
| --- | --- | --- | --- | --- |
| 9.5.2 | Advisor decision must be received before official notice | `admissions._ready_to_notify` | `test_srs_952_formal_acceptance_email_and_printable_letter`; `test_admin_no_final_recommendation_and_invalid_transcripts` | Advisor submits Recommend, sends to Administrator, Administrator issues notice |
| 9.5.2 | Email plus hard-copy format with program details | `issue_official_notice`; `official_decision_letter.html` | `test_srs_952_formal_acceptance_email_and_printable_letter` | View local SMTP capture; print letter; check name, degree, college, campus, term and contact |
| 9.5.3 | Applicant notifies Graduate College; Administrator processes | `notify_acceptance`, `process_acceptance` | `test_srs_953_954_applicant_intent_and_registrar_simulation` | Applicant accepts in portal; Administrator confirms before status changes |
| 9.5.4 | Registrar notification simulated for specified term | `registrar_simulations` table, view-only page | `test_srs_953_954_applicant_intent_and_registrar_simulation` | Confirm term and SIMULATION ONLY label; no external API |
| 9.5.5 | Accepted student record independent of intent | `create_student_record` | `test_srs_955_create_complete_student_record_with_transcript_before_intent` | Create student record while application status is Accepted, before intent |
| 9.5.5 | Source-derived personal, citizenship, residence, visa, ethnicity and education data | `_student_snapshot` | `test_srs_955_create_complete_student_record_with_transcript_before_intent`; `test_conops_requires_complete_education_history_before_student_record` | Review student record view, including ConOps full field list |
| 9.5.5 | Official transcript proof and creation timestamp | Private transcript endpoint, `created_at`, SHA-256 | `test_srs_955_create_complete_student_record_with_transcript_before_intent` | Upload verified PDF; confirm authorized download and timestamp |

## Manual end-to-end test

1. **Prepare:** Keep the existing `gdas.sqlite3` file; use a local SMTP capture server. Log in with a registered Advisor assigned to the relevant degree program and an Administrator account. Have a submitted, In Review application with complete ConOps personal, education and ethnicity fields. Confirm the degree program has approved resident and non-resident tuition amounts per unit.
2. **Advisor decision:** Advisor opens their Graduate College page, chooses **Recommend**, saves a rationale, then sends the decision to the selected Administrator. Verify the notification appears in local SMTP and is recorded in SQLite.
3. **9.5.2 positive:** Log in as Administrator, open **Admissions Processing**, select the applicant, and send the official decision. Verify an acceptance email is captured, status changes to **Accepted**, and the printable letter includes all relevant program details. Use **Print Letter** to produce the hard copy. The operator is responsible for physical mailing; printing does not assert postal delivery.
4. **9.5.5 positive, before intent:** Upload an actual PDF transcript received via an approved testing channel, certify it, choose the tuition classification and create the admitted-student record. Verify the stored record's education history, GPA, transcript reference, ethnicity, NetID, personal data, program, campus, term, tuition and generated creation date. Status remains Accepted until intent is processed.
5. **9.5.3 positive:** Sign in as the applicant, open **My Applications → Admission Decision**, select the acceptance checkbox and submit. Verify intent has a timestamp and status remains Accepted pending Administrator processing.
6. **9.5.4 positive:** Sign in as Administrator, process the received intent. Verify status changes to **Intent to Matriculate**, the applicant portal reflects processing, and the saved Registrar simulation shows the correct term. Confirm no real Registrar integration is used.
7. **Persistence:** Stop and restart UA-GDAS. Verify notice history, student record, transcript reference, intent, application status and Registrar simulation remain. Repeated actions must not create duplicate records.
8. **Rejection path:** Repeat with a separate In Review application. Advisor selects **Deny**, Administrator sends the denial notice. Verify the rejection email and printable letter. Acceptance, matriculation, and student record creation are blocked.
9. **Negative and access tests:** Defer cannot produce formal admission; absence of Advisor-to-Administrator communication blocks the official notice; failed SMTP does not finalize the application; wrong applicant cannot accept another person's offer; unauthenticated/non-admin accounts cannot retrieve student records or private transcripts; invalid, unverified or oversized transcripts are rejected; incomplete education fields block official record creation.

## Data handling and limitations

- **No live university system connections:** Registrar notification is a locally stored simulation, as mandated by the ConOps. SMTP is configured for the course project's local test service.
- **Hard-copy deliverable:** A print-ready letter is produced for staff to print and mail; physical delivery cannot be verified by the application.
- **Sensitive records:** Use fictional test identities and sample PDFs only. Do not upload real applicant transcripts or confidential records to publicly accessible resources.
- **Data accuracy:** Missing compulsory source fields cause a validation error. No applicant data or tuition eligibility is inferred or fabricated.
- **Control integrity:** Changing a stored official transcript after creation of an admitted student record is blocked until a separate amendment process is implemented.
- **History:** The system preserves existing application/account records and prevents duplicate formal notices or processing of the same intent.

## Completion criteria

Implementation is complete when automated tests pass, the manual workflow passes for both an acceptance and a denial, data survives a restart, and access controls prevent unauthorized changes. This checklist is a coursework verification plan; it is not certification for operation as a real University of Arizona admissions service.
