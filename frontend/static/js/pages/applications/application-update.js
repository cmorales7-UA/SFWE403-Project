document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".student-application-form");

  if (!form || !form.dataset.applicationId) {
    return;
  }

  const applicationId = form.dataset.applicationId;
  const returnUrl = form.dataset.returnUrl;
  const feedback = document.getElementById("application-feedback");
  const saveButton = form.querySelector('button[value="save_changes"]');

  let loaded = false;

  // Permit changes to incomplete applications.
  form.noValidate = true;

  if (saveButton) {
    saveButton.disabled = true;
  }

  function showMessage(message, isError = false) {
    if (!feedback) return;

    feedback.textContent = message;
    feedback.style.color = isError ? "#AB0520" : "#166534";
  }

  // Load the existing application from the backend.
  async function loadApplication() {
    try {
      const response = await fetch(
        `/api/applications/${encodeURIComponent(applicationId)}`,
        { credentials: "same-origin" },
      );

      const application = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof application.detail === "string"
            ? application.detail
            : "Unable to retrieve application.",
        );
      }

      const fields = application.fields || {};

      // Populate the existing application form.
      for (const control of form.elements) {
        if (!control.name || control.type === "file") {
          continue;
        }

        if (!Object.prototype.hasOwnProperty.call(fields, control.name)) {
          continue;
        }

        const value = fields[control.name];

        if (control.type === "radio" || control.type === "checkbox") {
          control.checked = control.value === value;
        } else {
          control.value = value ?? "";
        }
      }

      // Show application information that is not editable here.
      for (const name of ["campus", "term"]) {
        const control = form.elements.namedItem(name);

        if (control) {
          control.value = application[name] || "";
          control.disabled = true;
        }
      }

      const submissionDate = form.elements.namedItem("submission_date");

      if (submissionDate) {
        submissionDate.value = application.submission_date || "";
      }

      // Update conditional international applicant fields.
      const internationalOption = form.querySelector(
        'input[name="is_international_applicant"]:checked',
      );

      if (internationalOption) {
        internationalOption.dispatchEvent(
          new Event("change", { bubbles: true }),
        );
      }

      if (["Accepted", "Denied"].includes(application.status)) {
        showMessage(
          "This application has a final decision and cannot be modified.",
        );
        return;
      }

      loaded = true;

      if (saveButton) {
        saveButton.disabled = false;
      }
    } catch (error) {
      showMessage(error.message, true);
    }
  }

  // Save modified application fields.
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!loaded) {
      showMessage("The application must load before saving.", true);
      return;
    }

    // Documents need a separate upload endpoint.
    const hasNewFiles = [...form.querySelectorAll('input[type="file"]')].some(
      (input) => input.files.length > 0,
    );

    if (hasNewFiles) {
      showMessage(
        "Document uploads are not available yet. " +
          "Remove selected files before saving text changes.",
        true,
      );
      return;
    }

    const formData = new FormData(form);
    const fields = {};

    const excluded = new Set([
      "degree_program_id",
      "campus",
      "term",
      "submission_date",
      "application_action",
    ]);

    for (const [name, value] of formData.entries()) {
      if (typeof value === "string" && !excluded.has(name)) {
        fields[name] = value;
      }
    }

    if (Object.keys(fields).length === 0) {
      showMessage("No editable fields were found.", true);
      return;
    }

    if (saveButton) {
      saveButton.disabled = true;
    }

    try {
      const response = await fetch(
        `/api/applications/${encodeURIComponent(applicationId)}`,
        {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ fields }),
        },
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Unable to save the application.",
        );
      }

      showMessage("Application updated successfully.");

      if (
        returnUrl &&
        returnUrl.startsWith("/") &&
        !returnUrl.startsWith("//")
      ) {
        window.location.assign(returnUrl);
      } else {
        showMessage(
          "Application saved. Unable to determine the return page.",
          true,
        );
      }
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      if (saveButton) {
        saveButton.disabled = false;
      }
    }
  });

  loadApplication();
});
