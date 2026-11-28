(() => {
    "use strict";

    const form = document.getElementById("reports-form");
    const reportType = document.getElementById("report_type");
    const degreeProgram = document.getElementById("program_id");
    const requiredHint = document.getElementById("program-required");
    const fieldCount = document.getElementById("report-column-count");
    if (!form || !reportType || !degreeProgram) return;

    const outputFields = Array.from(
        form.querySelectorAll('input[name="fields"][type="checkbox"]')
    );
    const essentials = new Set([
        "full_name", "degree_program", "campus", "term",
        "application_status", "decision"
    ]);

    function updateSelectedCount() {
        if (!fieldCount) return;
        const count = outputFields.filter(field => field.checked).length;
        fieldCount.textContent = count
            ? count + " output column" + (count === 1 ? "" : "s") + " selected"
            : "Essential columns will be used";
    }

    function toggleReportSections() {
        const type = reportType.value;
        const isTailored = type === "tailored";
        degreeProgram.required = isTailored;
        degreeProgram.options[0].textContent = isTailored
            ? "Select a program"
            : "All authorized programs";
        if (requiredHint) requiredHint.hidden = !isTailored;

        for (const section of form.querySelectorAll("[data-report-scope]")) {
            const scope = section.dataset.reportScope;
            const visible = scope === "standard" ? !isTailored : scope === type;
            section.hidden = !visible;
            for (const control of section.querySelectorAll("input, select, textarea")) {
                control.disabled = !visible;
            }
        }
        updateSelectedCount();
    }

    form.querySelectorAll("[data-columns-action]").forEach(button => {
        button.addEventListener("click", () => {
            const all = button.dataset.columnsAction === "all";
            outputFields.forEach(field => {
                field.checked = all || essentials.has(field.value);
            });
            updateSelectedCount();
        });
    });

    outputFields.forEach(field => {
        field.addEventListener("change", updateSelectedCount);
    });

    // Reopen the optional filter section when a filter is already applied.
    const additional = document.getElementById("tailored-additional-filters");
    if (additional) {
        const hasActiveFilter = Array.from(
            additional.querySelectorAll('input[type="text"], select')
        ).some(control => control.value.trim() !== "");
        if (hasActiveFilter) additional.open = true;
    }

    reportType.addEventListener("change", toggleReportSections);
    toggleReportSections();
})();
