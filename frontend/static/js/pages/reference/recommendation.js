document.addEventListener("DOMContentLoaded", () => {
    const methodInputs = document.querySelectorAll(
        'input[name="submission_method"]'
    );

    const typedSection = document.getElementById(
        "typed-recommendation-section"
    );

    const uploadSection = document.getElementById(
        "upload-recommendation-section"
    );

    const typedInput = document.getElementById(
        "recommendation_text"
    );

    const fileInput = document.getElementById(
        "recommendation_file"
    );

    const selectedFileName = document.getElementById(
        "selected-file-name"
    );


    function updateSubmissionMethod() {
        const selectedMethod = document.querySelector(
            'input[name="submission_method"]:checked'
        );

        if (!selectedMethod) {
            return;
        }

        const isTyped =
            selectedMethod.value === "typed";


        typedSection.hidden = !isTyped;
        typedInput.disabled = !isTyped;
        typedInput.required = isTyped;


        uploadSection.hidden = isTyped;
        fileInput.disabled = isTyped;
        fileInput.required = !isTyped;
    }


    methodInputs.forEach((input) => {
        input.addEventListener(
            "change",
            updateSubmissionMethod
        );
    });


    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            selectedFileName.textContent =
                fileInput.files[0].name;
        } else {
            selectedFileName.textContent =
                "No file selected.";
        }
    });


    updateSubmissionMethod();
});