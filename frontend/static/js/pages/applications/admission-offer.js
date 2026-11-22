document.addEventListener("DOMContentLoaded", () => {
  const panel = document.querySelector(".admissions-offer[data-application-id]");
  const button = document.getElementById("accept-admission");
  const checkbox = document.getElementById("confirm-acceptance");
  const feedback = document.getElementById("admissions-feedback");
  if (!panel || !button || !checkbox) return;

  button.addEventListener("click", async () => {
    if (!checkbox.checked) {
      feedback.textContent = "Confirm that you accept the admission offer before notifying Graduate College.";
      feedback.style.color = "#AB0520";
      return;
    }
    button.disabled = true;
    feedback.textContent = "Recording your response...";
    feedback.style.color = "#0C234B";
    try {
      const response = await fetch(
        "/api/admissions/" + encodeURIComponent(panel.dataset.applicationId) + "/intent",
        {method:"POST", credentials:"same-origin"}
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Unable to record your acceptance.");
      }
      window.location.reload();
    } catch (error) {
      feedback.textContent = error.message || "Unable to record acceptance.";
      feedback.style.color = "#AB0520";
      button.disabled = false;
    }
  });
});
