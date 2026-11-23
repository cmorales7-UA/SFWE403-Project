// The administrator form edits the existing account through the persistent API.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".user-edit-form[data-user-id]");
  if (!form) return;

  const feedback = document.getElementById("user-save-feedback");
  const submitButton = form.querySelector('button[type="submit"]');
  const roleSelect = form.querySelector("#user_type");
  const programSection = document.getElementById("user-program-assignments");

  function showMessage(text, isError = false) {
    if (!feedback) return;
    feedback.textContent = text;
    feedback.style.color = isError ? "#AB0520" : "#166534";
  }

  function toggleProgramAssignments() {
    if (!programSection || !roleSelect) return;
    const isAssignedRole = ["advisor", "reviewer"].includes(roleSelect.value);
    programSection.hidden = !isAssignedRole;
  }

  if (roleSelect) roleSelect.addEventListener("change", toggleProgramAssignments);
  toggleProgramAssignments();

  function requestError(body, status) {
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      return body.detail.map(item => item.msg || "Invalid value").join("; ");
    }
    return `Unable to save account (HTTP ${status}).`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const values = new FormData(form);
    const fields = [
      "username", "first_name", "last_name", "email",
      "phone", "net_id", "user_type",
    ];
    const payload = {};
    for (const field of fields) {
      payload[field] = String(values.get(field) ?? "").trim();
    }
    if (programSection) {
      payload.assigned_program_ids = ["advisor", "reviewer"].includes(payload.user_type)
        ? values.getAll("assigned_program_ids").map(Number)
        : [];
    }
    const newPassword = String(values.get("new_password") ?? "");
    if (newPassword) payload.new_password = newPassword;

    if (submitButton) submitButton.disabled = true;
    showMessage("Saving account changes...");

    try {
      const response = await fetch(
        `/api/users/${encodeURIComponent(form.dataset.userId)}`,
        {
          method: "PATCH",
          credentials: "same-origin",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        }
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(requestError(body, response.status));

      // Reload the account from SQLite so values reflect the committed result.
      const params = new URLSearchParams(window.location.search);
      params.set("user", String(form.dataset.userId));
      params.set("saved", "1");
      window.location.assign(`/administrator/manage-users?${params.toString()}`);
    } catch (error) {
      showMessage(error.message || "Unable to save account.", true);
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
});
