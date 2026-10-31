
/*
 * SRS 9.4.3 - Application Communication with Applicant
 *
 * Allows an Advisor or Administrator to send an email
 * to an applicant before a final application decision.
 */

document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("applicant-message-form");

    // Only initialize when the communication form exists.
    if (!form) {
        return;
    }

    const applicationId = form.dataset.applicationId;

    const subjectInput = document.getElementById(
        "application-message-subject"
    );

    const bodyInput = document.getElementById(
        "application-message-body"
    );

    const sendButton = document.getElementById(
        "send-application-message"
    );

    const feedback = document.getElementById(
        "application-message-feedback"
    );

    if (
        !applicationId ||
        !subjectInput ||
        !bodyInput ||
        !sendButton ||
        !feedback
    ) {
        return;
    }

    // Display success or error messages.
    function showFeedback(message, isError = false) {
        feedback.textContent = message;
        feedback.style.color = isError ? "#AB0520" : "#28724f";
    }

    // Send application communication.
    form.addEventListener("submit", async (event) => {

        event.preventDefault();

        const subject = subjectInput.value.trim();
        const body = bodyInput.value.trim();

        // Validate required fields.
        if (!subject || !body) {
            showFeedback(
                "Please enter both a subject and message.",
                true
            );
            return;
        }

        // Prevent duplicate submissions.
        sendButton.disabled = true;
        sendButton.textContent = "Sending...";

        showFeedback("");

        try {

            const response = await fetch(
                `/api/applications/${encodeURIComponent(applicationId)}/messages`,
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        subject: subject,
                        body: body
                    })
                }
            );

            const result = await response.json().catch(() => ({}));

            if (!response.ok) {

                let errorMessage = "Unable to send the email.";

                if (typeof result.detail === "string") {
                    errorMessage = result.detail;
                }

                throw new Error(errorMessage);
            }

            showFeedback(
                "Email sent successfully."
            );

            // Clear the form after successful delivery.
            form.reset();

        } catch (error) {

            showFeedback(
                error.message || "An error occurred while sending the email.",
                true
            );

        } finally {

            sendButton.disabled = false;
            sendButton.textContent = "Send Email";

        }

    });

});
