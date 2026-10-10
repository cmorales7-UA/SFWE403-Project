document.addEventListener("DOMContentLoaded", () => {
    // International applicant fields
    const internationalOptions = document.querySelectorAll(
        'input[name="is_international_applicant"]'
    );

    const internationalSection = document.getElementById(
        "international-applicant-fields"
    );

    if (internationalSection && internationalOptions.length > 0) {
        const internationalFields = internationalSection.querySelectorAll(
            "input, select, textarea"
        );

        function updateInternationalSection() {
            const selectedOption = document.querySelector(
                'input[name="is_international_applicant"]:checked'
            );

            const isInternational =
                selectedOption &&
                selectedOption.value === "yes";

            internationalSection.hidden = !isInternational;

            internationalFields.forEach((field) => {
                field.disabled = !isInternational;
                field.required = isInternational;
            });
        }

        internationalOptions.forEach((option) => {
            option.addEventListener(
                "change",
                updateInternationalSection
            );
        });

        updateInternationalSection();
    }


    // PDF upload validation
    const pdfUploadFields = document.querySelectorAll(
        'input[type="file"][accept*="pdf", accept*=".docx", accept*=".doc"]'
    );

    const MAX_FILE_SIZE = 10 * 1024 * 1024;

    pdfUploadFields.forEach((field) => {
        field.addEventListener("change", () => {
            const file = field.files[0];

            if (!file) {
                return;
            }

            const fileName = file.name.toLowerCase();
            const isPdfExtension = fileName.endsWith(".pdf");
            const isPdfType =
                file.type === "application/pdf" ||
                file.type === "";

            if (!isPdfExtension || !isPdfType) {
                alert("Only PDF files are allowed.");

                field.value = "";
                return;
            }

            if (file.size > MAX_FILE_SIZE) {
                alert("PDF files must be 10 MB or smaller.");

                field.value = "";
            }
        });
    });
});