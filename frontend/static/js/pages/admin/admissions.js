// SRS 9.5.2–9.5.5, Graduate College admissions processing.
// Only the authenticated backend can change official statuses or student records.
document.addEventListener("DOMContentLoaded", () => {
  const panel = document.querySelector("[data-application-id]");
  if (!panel) return;
  const id = Number(panel.dataset.applicationId);
  const feedback = document.getElementById("admissions-feedback");

  function inform(text, error = false) {
    if (!feedback) return;
    feedback.textContent = text;
    feedback.style.color = error ? "#AB0520" : "#166534";
  }

  function serverError(body, status) {
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      return body.detail.map(item => item.msg || "Invalid field").join("; ");
    }
    return "Request failed (HTTP " + status + ").";
  }

  async function send(path, options = {}) {
    const response = await fetch("/api/admissions/" + encodeURIComponent(id) + "/" + path, {
      method: "POST",
      credentials: "same-origin",
      ...options
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(serverError(body, response.status));
    return body;
  }

  function wireClick(selector, path, confirmation) {
    const button = document.querySelector(selector);
    if (!button) return;
    button.addEventListener("click", async () => {
      if (confirmation && !window.confirm(confirmation)) return;
      button.disabled = true;
      inform("Saving changes...");
      try {
        await send(path);
        window.location.reload();
      } catch (error) {
        inform(error.message || "Unable to process request", true);
        button.disabled = false;
      }
    });
  }

  wireClick(
    "#send-official-notice",
    "official-notice",
    "Send the final admission decision email and prepare a printable letter? This action cannot be undone."
  );
  wireClick(
    "#process-intent",
    "process-intent",
    "Confirm the applicant officially notified Graduate College of acceptance? The application status will change to Intent to Matriculate."
  );

  const recordForm = document.getElementById("create-student-record-form");
  if (recordForm) recordForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!recordForm.reportValidity()) return;
    const button = recordForm.querySelector("button[type='submit']");
    button.disabled = true;
    inform("Creating admitted student record...");
    try {
      await send("student-record", {
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          tuition_classification: new FormData(recordForm).get("tuition_classification")
        })
      });
      window.location.reload();
    } catch (error) {
      inform(error.message || "Student record could not be created", true);
      button.disabled = false;
    }
  });

  const transcriptForm = document.getElementById("official-transcript-form");
  if (transcriptForm) transcriptForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!transcriptForm.reportValidity()) return;
    const button = transcriptForm.querySelector("button[type='submit']");
    const data = new FormData(transcriptForm);
    button.disabled = true;
    inform("Storing verified transcript...");
    try {
      await send("official-transcript", {body: data});
      window.location.reload();
    } catch (error) {
      inform(error.message || "Transcript could not be saved", true);
      button.disabled = false;
    }
  });
});
