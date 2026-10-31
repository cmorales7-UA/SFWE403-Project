
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("preliminary-review-form");

    if (!form) {
        return;
    }

    const applicationId = form.dataset.applicationId;
    const feedback = document.getElementById(
        "preliminary-review-feedback"
    );

    const comments = document.getElementById("review_comments");
    const missing = document.getElementById("missing_information");
    const informationButton = document.getElementById(
        "request-information-button"
    );

    const referenceButtons = [
        ...document.querySelectorAll(".reference-request-button")
    ];

    const buttons = [
        form.querySelector('button[type="submit"]'),
        informationButton,
        ...referenceButtons
    ].filter(Boolean);

    const disabledButtons = new Set(
        buttons.filter(button => button.disabled)
    );

    let busy = false;

    function showMessage(message, isError = false) {
        feedback.textContent = message;
        feedback.style.color = isError ? "#AB0520" : "#166534";
    }

    function setBusy(value) {
        busy = value;

        buttons.forEach(button => {
            button.disabled = value || disabledButtons.has(button);
        });
    }

    async function postJson(endpoint, payload = {}) {
        const response = await fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = data.detail;

            throw new Error(
                typeof detail === "string"
                    ? detail
                    : `Request failed (HTTP ${response.status}).`
            );
        }

        return data;
    }

    async function savePreliminaryReview() {
        const result = await postJson(
            `/api/applications/${encodeURIComponent(applicationId)}/preliminary-review`,
            {
                review_comments: comments.value,
                missing_information: missing.value
            }
        );

        const status = document.getElementById(
            "review-application-status"
        );

        if (status) {
            status.textContent = result.status;
        }

        return result;
    }

    // Save preliminary review.
    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (busy) return;

        setBusy(true);
        showMessage("Saving review...");

        try {
            await savePreliminaryReview();
            showMessage("Preliminary review saved successfully.");
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            setBusy(false);
        }
    });

    // Request missing information from the applicant.
    informationButton.addEventListener("click", async () => {
        if (busy) return;

        if (!missing.value.trim()) {
            showMessage(
                "Identify the missing information before sending a request.",
                true
            );
            return;
        }

        if (!window.confirm(
            "Send an additional information request to the applicant?"
        )) {
            return;
        }

        setBusy(true);
        showMessage("Sending request...");

        try {
            // Save the latest review before requesting information.
            await savePreliminaryReview();

            await postJson(
                `/api/applications/${encodeURIComponent(applicationId)}/request-information`
            );

            showMessage("Information request sent successfully.");
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            setBusy(false);
        }
    });

    // Request a recommendation letter from a selected reference.
    referenceButtons.forEach(button => {
        button.addEventListener("click", async () => {
            if (busy) return;

            const referenceNumber = Number(
                button.dataset.referenceNumber
            );

            const referenceName =
                button.dataset.referenceName || "this reference";

            if (!window.confirm(
                `Send a recommendation request to ${referenceName}?`
            )) {
                return;
            }

            setBusy(true);
            showMessage("Sending recommendation request...");

            try {
                await savePreliminaryReview();

                await postJson(
                    `/api/applications/${encodeURIComponent(applicationId)}/recommendation-requests`,
                    {
                        reference_number: referenceNumber
                    }
                );

                button.textContent = "Request Sent";
                disabledButtons.add(button);

                showMessage(
                    "Recommendation request sent successfully."
                );
            } catch (error) {
                showMessage(error.message, true);
            } finally {
                setBusy(false);
            }
        });
    });
});
