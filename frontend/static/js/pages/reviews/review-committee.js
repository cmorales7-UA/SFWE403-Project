
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("review-assignment-form");
    const notificationForm = document.getElementById("review-notification-form");

    if (!form || !notificationForm) return;

    const program = document.getElementById("committee-program");
    const deadline = document.getElementById("committee-deadline");
    const saveButton = document.getElementById("save-review-assignments");
    const sendButton = document.getElementById("send-review-notifications");
    const assignmentFeedback = document.getElementById("committee-assignment-feedback");
    const tableFeedback = document.getElementById("committee-table-feedback");
    const applicationItems = [...form.querySelectorAll(".committee-application-option")];
    const reviewerItems = [...form.querySelectorAll(".committee-reviewer-option")];
    const applicationEmpty = document.getElementById("committee-no-applications");
    const reviewerEmpty = document.getElementById("committee-no-reviewers");
    const applicationEmptyText = document.getElementById("committee-no-applications-text");
    const reviewerEmptyText = document.getElementById("committee-no-reviewers-text");
    const reviewLink = document.getElementById("committee-review-app-link");
    const applicationCount = document.getElementById("committee-application-count");
    const reviewerCount = document.getElementById("committee-reviewer-count");
    const selectAll = document.getElementById("committee-select-all");
    const notificationSelection = document.getElementById("committee-notification-selection");
    const table = document.getElementById("committee-assignments-body");
    const flashKey = "gdas-review-committee-flash";
    const programKey = "gdas-review-committee-program";

    let busy = false;

    function today() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");

        return `${year}-${month}-${day}`;
    }

    function message(element, value, state = "") {
        element.textContent = value;
        element.dataset.state = state;
    }

    function selected(root, selector) {
        return [...root.querySelectorAll(selector)]
            .filter(input => input.checked && !input.disabled);
    }

    function ids(inputs) {
        return inputs.map(input => Number(input.value));
    }

    function updateSaveState() {
        const apps = selected(form, ".committee-application-checkbox");
        const reviewers = selected(form, ".committee-reviewer-checkbox");

        applicationCount.textContent = apps.length
            ? `(${apps.length} selected)`
            : "";

        reviewerCount.textContent = reviewers.length
            ? `(${reviewers.length} selected)`
            : "";

        saveButton.disabled =
            busy ||
            !program.value ||
            !apps.length ||
            !reviewers.length ||
            !deadline.value ||
            deadline.value < today();
    }

    function filterOptions() {
        const programId = program.value;
        let visibleApps = 0;
        let visibleReviewers = 0;

        for (const item of applicationItems) {
            const show = Boolean(programId) &&
                item.dataset.programId === programId;

            item.hidden = !show;

            if (!show) {
                item.querySelector("input").checked = false;
            }

            if (show) visibleApps++;
        }

        for (const item of reviewerItems) {
            const allowedPrograms = (
                item.dataset.programIds || ""
            ).split(",").map(value => value.trim());

            const show = Boolean(programId) &&
                allowedPrograms.includes(programId);

            item.hidden = !show;

            if (!show) {
                item.querySelector("input").checked = false;
            }

            if (show) visibleReviewers++;
        }

        applicationEmpty.hidden = visibleApps > 0;
        reviewerEmpty.hidden = visibleReviewers > 0;

        applicationEmptyText.textContent = !programId
            ? "Select a degree program to view applications."
            : "No applications are ready for committee review.";

        reviewerEmptyText.textContent = !programId
            ? "Select a degree program to view reviewers."
            : "No reviewers are assigned to this program.";

        reviewLink.hidden = !programId || visibleApps > 0;

        updateSaveState();
    }

    function pendingAssignments() {
        return [...notificationForm.querySelectorAll(
            ".committee-assignment-checkbox"
        )].filter(input => !input.disabled);
    }

    function updateNotificationState() {
        const pending = pendingAssignments();
        const checked = pending.filter(input => input.checked);

        selectAll.disabled = busy || pending.length === 0;

        selectAll.checked =
            pending.length > 0 &&
            checked.length === pending.length;

        selectAll.indeterminate =
            checked.length > 0 &&
            checked.length < pending.length;

        sendButton.disabled = busy || checked.length === 0;

        notificationSelection.textContent = checked.length
            ? `${checked.length} assignment${checked.length === 1 ? "" : "s"} selected`
            : "Select assignments to notify reviewers.";
    }

    function updateDeadlineButton(row) {
        const input = row.querySelector(".committee-deadline-input");
        const button = row.querySelector(".committee-update-deadline");

        if (!input || !button) return;

        const changed = input.value !== input.dataset.originalDate;

        button.hidden = !changed;
        button.disabled =
            busy ||
            !changed ||
            !input.value ||
            input.value < today();
    }

    function setBusy(value) {
        busy = value;
        updateSaveState();
        updateNotificationState();

        table.querySelectorAll("tr").forEach(updateDeadlineButton);
    }

    async function postJson(path, payload) {
        let response;

        try {
            response = await fetch(path, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });
        } catch {
            throw new Error(
                "Unable to connect to UA-GDAS. Check that the server is running."
            );
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = data.detail;

            const errorText = typeof detail === "string"
                ? detail
                : Array.isArray(detail)
                    ? detail.map(item => item.msg || "Invalid request").join("; ")
                    : `Request failed (HTTP ${response.status}).`;

            throw new Error(errorText);
        }

        return data;
    }

    function refreshWithMessage(target, value) {
        try {
            sessionStorage.setItem(
                flashKey,
                JSON.stringify({ target, value })
            );
        } catch {
            // The saved records will still appear after reloading.
        }

        window.location.reload();
    }

    deadline.min = today();

    table.querySelectorAll(".committee-deadline-input").forEach(input => {
        input.min = today();
    });

    try {
        const savedProgram = sessionStorage.getItem(programKey);

        if (
            savedProgram &&
            [...program.options].some(option => option.value === savedProgram)
        ) {
            program.value = savedProgram;
        }

        const flash = JSON.parse(
            sessionStorage.getItem(flashKey) || "null"
        );

        sessionStorage.removeItem(flashKey);

        if (flash && typeof flash.value === "string") {
            message(
                flash.target === "table"
                    ? tableFeedback
                    : assignmentFeedback,
                flash.value,
                "success"
            );
        }
    } catch {
        // Session storage is optional.
    }

    filterOptions();
    updateNotificationState();

    program.addEventListener("change", () => {
        message(assignmentFeedback, "");

        try {
            sessionStorage.setItem(programKey, program.value);
        } catch {
            // The program can still be selected normally.
        }

        filterOptions();
    });

    form.addEventListener("change", event => {
        if (event.target !== program) {
            updateSaveState();
        }
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (busy) return;

        const applicationIds = ids(
            selected(form, ".committee-application-checkbox")
        );

        const reviewerIds = ids(
            selected(form, ".committee-reviewer-checkbox")
        );

        if (
            !program.value ||
            !applicationIds.length ||
            !reviewerIds.length ||
            !deadline.value ||
            deadline.value < today()
        ) {
            message(
                assignmentFeedback,
                "Select a program, at least one application and reviewer, and a valid deadline.",
                "error"
            );
            return;
        }

        setBusy(true);
        message(assignmentFeedback, "Saving assignments...");

        try {
            await postJson("/api/review-committee/assignments", {
                application_ids: applicationIds,
                reviewer_ids: reviewerIds,
                due_date: deadline.value
            });

            refreshWithMessage(
                "assignment",
                "Assignments saved. Select pending assignments below to send notifications."
            );
        } catch (error) {
            message(assignmentFeedback, error.message, "error");
            setBusy(false);
        }
    });

    notificationForm.addEventListener("change", event => {
        if (event.target.matches(".committee-assignment-checkbox")) {
            updateNotificationState();
        }

        if (event.target.matches(".committee-deadline-input")) {
            updateDeadlineButton(event.target.closest("tr"));
        }
    });

    selectAll.addEventListener("change", () => {
        pendingAssignments().forEach(input => {
            input.checked = selectAll.checked;
        });

        updateNotificationState();
    });

    table.addEventListener("click", async event => {
        const button = event.target.closest(".committee-update-deadline");

        if (!button || busy || button.disabled) return;

        const row = button.closest("tr");
        const input = row.querySelector(".committee-deadline-input");

        if (!input.value || input.value < today()) {
            message(
                tableFeedback,
                "Choose a current or future deadline.",
                "error"
            );
            return;
        }

        setBusy(true);
        message(tableFeedback, "Updating deadline...");

        try {
            await postJson("/api/review-committee/assignments", {
                application_ids: [
                    Number(button.dataset.applicationId)
                ],
                reviewer_ids: [
                    Number(button.dataset.reviewerId)
                ],
                due_date: input.value
            });

            refreshWithMessage(
                "table",
                "Deadline updated. Send a new notification if the reviewer needs the revised date."
            );
        } catch (error) {
            message(tableFeedback, error.message, "error");
            setBusy(false);
        }
    });

    notificationForm.addEventListener("submit", async event => {
        event.preventDefault();

        if (busy) return;

        const checkboxes = selected(
            notificationForm,
            ".committee-assignment-checkbox"
        );

        if (!checkboxes.length) {
            message(
                tableFeedback,
                "Select at least one assignment to notify.",
                "error"
            );
            return;
        }

        const recipients = [
            ...new Set(
                checkboxes
                    .map(input => input.dataset.reviewerEmail)
                    .filter(Boolean)
            )
        ];

        const description = recipients.slice(0, 5).join("\n");
        const remaining = recipients.length > 5
            ? `\n...and ${recipients.length - 5} more`
            : "";

        const confirmed = window.confirm(
            `Send review notifications to ${recipients.length} reviewer(s)?\n\n${description}${remaining}`
        );

        if (!confirmed) return;

        setBusy(true);
        message(tableFeedback, "Sending notifications...");

        try {
            await postJson("/api/review-committee/notifications", {
                assignment_ids: ids(checkboxes)
            });

            refreshWithMessage(
                "table",
                "Notifications sent. The assignment table has been updated."
            );
        } catch (error) {
            message(
                tableFeedback,
                `${error.message} If several reviewers were selected, check their status before retrying.`,
                "error"
            );

            setBusy(false);
        }
    });
});
