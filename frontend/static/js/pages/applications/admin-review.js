document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("graduate-college-review-form");
  if (!form) return;

  const button = form.querySelector('button[type="submit"]');
  const feedback = document.getElementById("graduate-college-review-feedback");

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (button.disabled) return;
    button.disabled = true;
    feedback.textContent = "";
    try {
      const response = await fetch(
        "/api/applications/" + encodeURIComponent(form.dataset.applicationId) + "/graduate-college-review",
        {
          method: "PUT",
          credentials: "same-origin",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({notes: form.elements.namedItem("notes").value})
        }
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = typeof data.detail === "string"
          ? data.detail : "Unable to save notes.";
        throw new Error(message);
      }
      feedback.textContent = "Notes saved.";
      feedback.style.color = "#166534";
    } catch (error) {
      feedback.textContent = error.message || "Unable to save notes.";
      feedback.style.color = "#AB0520";
    } finally {
      button.disabled = false;
    }
  });
});
