// IT Support can update account contact information, not privileged roles.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".user-edit-form[data-user-id]");
  if (!form) return;

  const feedback = document.getElementById("it-user-save-feedback");
  const button = form.querySelector('button[type="submit"]');
  const allowed = ["username", "first_name", "last_name", "net_id", "phone", "email"];
  const show = (text, error = false) => {
    if (!feedback) return;
    feedback.textContent = text;
    feedback.style.color = error ? "#AB0520" : "#166534";
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const values = new FormData(form);
    const payload = {};
    for (const key of allowed) payload[key] = String(values.get(key) ?? "").trim();

    button.disabled = true;
    show("Saving account...");
    try {
      const response = await fetch(
        `/api/users/${encodeURIComponent(form.dataset.userId)}`, {
          method: "PATCH",
          credentials: "same-origin",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        }
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === "string"
          ? body.detail
          : Array.isArray(body.detail)
            ? body.detail.map(value => value.msg).join("; ")
            : `Unable to save account (HTTP ${response.status})`;
        throw new Error(detail);
      }
      const params = new URLSearchParams(window.location.search);
      params.set("user", String(form.dataset.userId));
      params.set("saved", "1");
      window.location.assign(`/it-support/manage-users?${params.toString()}`);
    } catch (error) {
      show(error.message || "Unable to save account.", true);
    } finally {
      button.disabled = false;
    }
  });
});
