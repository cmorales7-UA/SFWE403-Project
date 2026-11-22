document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("graduate-college-review-form");
  if (!form) return;

  const button = form.querySelector('button[type="submit"]');
  const feedback = document.getElementById("graduate-college-review-feedback");
  const recommendation = form.querySelector("#recommendation");
  const rationale = form.querySelector("#advisor_rationale");

  if (!button) return;

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (button.disabled) return;

    const payload = {
      review_comments: form.elements.namedItem("review_comments").value
    };

    if (recommendation && !recommendation.disabled) {
      payload.decision = recommendation.value;
      payload.rationale = rationale.value;
      payload.decision_version = Number(form.dataset.decisionVersion);
      if (!payload.decision || !payload.rationale.trim()) {
        feedback.textContent = "Select a recommendation and enter a rationale.";
        feedback.style.color = "#AB0520";
        return;
      }
    }

    button.disabled = true;
    feedback.textContent = "";
    try {
      const response = await fetch(
        "/api/applications/" + encodeURIComponent(form.dataset.applicationId) + "/graduate-college-review",
        {
          method: "PUT",
          credentials: "same-origin",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        }
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map(item => item.msg).join("; ")
            : "Unable to save review.";
        throw new Error(detail);
      }
      if (data.decision_version) {
        form.dataset.decisionVersion = String(data.decision_version);
      }
      const notification = document.getElementById("advisor-notification-state");
      if (data.notification_required && notification) {
        notification.textContent = "Notification: Pending";
      }
      feedback.textContent = data.notification_required
        ? "Review saved. The Advisor must resend the updated recommendation."
        : "Review saved.";
      feedback.style.color = "#166534";
    } catch (error) {
      feedback.textContent = error.message || "Unable to save review.";
      feedback.style.color = "#AB0520";
    } finally {
      button.disabled = false;
    }
  });
});
