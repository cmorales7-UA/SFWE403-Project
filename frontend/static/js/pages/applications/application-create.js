
document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".student-application-form");

    if (!form || !form.querySelector(
        'button[value="submit_application"]'
    )) {
        return;
    }

    const feedback = document.getElementById(
        "application-feedback"
    );

    const buttons = form.querySelectorAll(
        'button[type="submit"]'
    );

    function showMessage(message, isError = false) {
        if (!feedback) return;

        feedback.textContent = message;
        feedback.style.color = isError ? "#AB0520" : "#166534";
    }

    function setSaving(saving) {
        buttons.forEach(button => {
            button.disabled = saving;
        });
    }

    function getErrorMessage(data, status) {
        if (typeof data.detail === "string") {
            return data.detail;
        }

        if (Array.isArray(data.detail)) {
            return data.detail.map(error => error.msg).join("; ");
        }

        return `Unable to save application (HTTP ${status}).`;
    }

    form.addEventListener("submit", async (event) => {

        // Prevent the browser from sending form fields in the URL.
        event.preventDefault();

        const action = event.submitter?.value || "save_draft";
        const submitted = action === "submit_application";

        const formData = new FormData(form);

        const programId = Number(
            formData.get("degree_program_id")
        );

        const campus = formData.get("campus");
        const term = formData.get("term");

        // Validate the selected degree program.
        if (!programId || !campus || !term) {
            showMessage(
                "Select a degree program, campus, and term.",
                true
            );
            return;
        }

        const fields = {};

        const excludedFields = new Set([
            "degree_program_id",
            "campus",
            "term",
            "submission_date",
            "application_action"
        ]);

        // Collect text fields for the backend.
        for (const [name, value] of formData.entries()) {

            if (excludedFields.has(name)) {
                continue;
            }

            // File uploads require a separate endpoint.
            if (typeof value !== "string") {
                continue;
            }

            fields[name] = value;
        }

        // Match the backend ApplicationCreate schema.
        const payload = {
            program_id: programId,
            campus: campus,
            term: term,
            fields: fields,
            submitted: submitted
        };

        setSaving(true);
        showMessage("Saving application...");

        try {
            const response = await fetch("/api/applications", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    getErrorMessage(result, response.status)
                );
            }

            // Backend successfully created the application.
            showMessage(
                submitted
                    ? "Application record submitted successfully."
                    : "Application draft saved successfully."
            );

            window.location.assign("/applicant/applications");

        } catch (error) {
            showMessage(error.message, true);

        } finally {
            setSaving(false);
        }

    });

});
