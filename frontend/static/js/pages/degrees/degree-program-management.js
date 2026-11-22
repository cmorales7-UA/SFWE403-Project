// Create and modify degree programs using the existing persistent FastAPI endpoints.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("degree-program-form");
  if (!form) return;

  const mode = form.dataset.mode;
  const role = form.dataset.role;
  const selector = form.querySelector("#degree_program_id");
  const feedback = document.getElementById("degree-program-feedback");
  const submit = form.querySelector('button[type="submit"]');

  const message = (value, error = false) => {
    if (!feedback) return;
    feedback.textContent = value;
    feedback.style.color = error ? "#AB0520" : "#166534";
  };

  // A server-rendered reload supplies saved program data in every form field.
  if (mode === "modify") {
    if (submit) submit.disabled = !form.dataset.programId;
    if (selector) {
      selector.addEventListener("change", () => {
        const id = Number(selector.value);
        if (!Number.isSafeInteger(id) || id <= 0) return;
        window.location.assign(
          `/${role}/modify-degree-program?degree_id=${encodeURIComponent(id)}`
        );
      });
    }
    if (!form.dataset.programId) {
      message("Select an existing degree program before making changes.");
    }
  }

  function getError(body, status) {
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      return body.detail.map(item => item.msg || "Invalid value").join("; ");
    }
    return `Unable to save degree program (HTTP ${status}).`;
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (mode === "modify" && !form.dataset.programId) {
      message("Select a degree program first.", true);
      return;
    }
    if (!form.reportValidity()) return;

    const data = new FormData(form);
    const campus = data.getAll("campus_offered").map(String);
    const terms = data.getAll("terms_offered").map(String);
    if (campus.length === 0) {
      message("Select at least one campus.", true);
      return;
    }

    const fields = [
      "degree_name", "degree_level", "degree_college", "degree_description",
      "degree_requirements", "application_deadline", "application_fee",
      "sponsor_question", "ta_ra_question", "funding_question",
      "english_test_question", "english_score_question",
      "other_requirements", "program_contact",
    ];
    const payload = {};
    for (const field of fields) {
      payload[field] = String(data.get(field) ?? "").trim();
    }
    payload.campus_offered = campus;
    payload.terms_offered = terms;

    const id = Number(form.dataset.programId);
    const updating = mode === "modify";
    const url = updating
      ? `/api/programs/${encodeURIComponent(id)}`
      : "/api/programs";

    if (submit) submit.disabled = true;
    message(updating ? "Saving changes..." : "Creating degree program...");

    try {
      const response = await fetch(url, {
        method: updating ? "PUT" : "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(getError(body, response.status));
      if (!body.id) throw new Error("Server returned no degree program ID.");

      message(updating ? "Degree program updated successfully." : "Degree program created successfully.");

      // Reload the record from SQLite, so the displayed values match the DB.
      window.location.assign(
        `/${role}/modify-degree-program?degree_id=${encodeURIComponent(body.id)}`
      );
    } catch (error) {
      message(error.message || "Unable to save degree program.", true);
    } finally {
      if (submit) submit.disabled = false;
    }
  });
});
