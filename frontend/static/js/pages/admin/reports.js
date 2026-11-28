(() => {
    "use strict";

    const typeSelector = document.getElementById("report_type");
    const form = document.getElementById("reports-form");
    if (!typeSelector || !form) return;

    function updateReportControls() {
        const activeType = typeSelector.value;
        for (const section of form.querySelectorAll("[data-report-scope]")) {
            const active = section.dataset.reportScope === activeType;
            section.hidden = !active;
            for (const control of section.querySelectorAll("input, select, textarea")) {
                control.disabled = !active;
            }
        }
    }

    typeSelector.addEventListener("change", updateReportControls);
    updateReportControls();
})();
