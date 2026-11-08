document.addEventListener("DOMContentLoaded", () => {
    const $ = id => document.getElementById(id);

    const list = $("gc-application-list");
    const search = $("gc-search");
    const detailContent = $("gc-detail-content");
    const emptySelection = $("gc-selection-empty");
    const form = $("gc-decision-form");
    const decisionInput = $("gc-decision");
    const rationaleInput = $("gc-rationale");
    const saveButton = $("gc-save-decision");
    const administratorInput = $("gc-administrator");
    const sendButton = $("gc-send-notification");

    if (!list || !form) return;

    let applications = [];
    let details = null;
    let selectedId = null;
    let busy = false;
    let requestNumber = 0;

    function feedback(id, message, error = false) {
        const element = $(id);
        element.textContent = message;
        element.dataset.state = error ? "error" : "success";
    }

    async function api(path, method = "GET", payload = null) {
        let response;

        try {
            response = await fetch(path, {
                method,
                credentials: "same-origin",
                headers: payload === null
                    ? {}
                    : { "Content-Type": "application/json" },
                ...(payload === null
                    ? {}
                    : { body: JSON.stringify(payload) }),
            });
        } catch {
            throw new Error(
                "Could not connect to UA-GDAS. Check that the server is running."
            );
        }

        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = result.detail;

            const message = typeof detail === "string"
                ? detail
                : Array.isArray(detail)
                    ? detail.map(item => item.msg || "Invalid request").join("; ")
                    : `Request failed (HTTP ${response.status}).`;

            throw new Error(message);
        }

        return result;
    }

    function element(tag, className, text) {
        const item = document.createElement(tag);

        if (className) item.className = className;
        if (text !== undefined) item.textContent = String(text);

        return item;
    }

    function notice(message) {
        list.replaceChildren(element("p", "gc-empty", message));
    }

    function isSentForCurrentDecision() {
        if (!details || !details.decision) return false;

        return (details.notifications || []).some(item =>
            Number(item.decision_version) === Number(details.decision.version)
        );
    }

    function renderList() {
        const term = search.value.trim().toLowerCase();

        const filtered = applications.filter(app =>
            `${app.applicant_name} ${app.degree_program} ${app.term} ${app.id}`
                .toLowerCase()
                .includes(term)
        );

        list.replaceChildren();

        if (!filtered.length) {
            notice(
                applications.length
                    ? "No matching applications."
                    : "No applications are currently in review."
            );
            return;
        }

        filtered.forEach(app => {
            const row = element("button", "gc-application-row");

            row.type = "button";
            row.dataset.applicationId = String(app.id);

            row.classList.toggle(
                "active",
                Number(app.id) === selectedId
            );

            row.setAttribute(
                "aria-pressed",
                String(Number(app.id) === selectedId)
            );

            const title = element(
                "strong",
                "gc-app-title",
                app.applicant_name
            );

            const program = element(
                "span",
                "gc-app-program",
                app.degree_program
            );

            const footer = element("span", "gc-app-footer");

            footer.append(
                element("span", "", app.term),
                element(
                    "span",
                    "gc-app-state",
                    app.notified
                        ? "Notified"
                        : app.decision
                            ? "Decision saved"
                            : "No decision"
                )
            );

            row.append(title, program, footer);
            list.appendChild(row);
        });
    }

    function hasUnsavedChanges() {
        const saved = details && details.decision;

        if (!saved) {
            return Boolean(
                decisionInput.value || rationaleInput.value.trim()
            );
        }

        return decisionInput.value !== saved.decision ||
            rationaleInput.value.trim() !== saved.rationale;
    }

    function updateButtons() {
        const valid = Boolean(
            decisionInput.value && rationaleInput.value.trim()
        );

        saveButton.disabled =
            busy ||
            !details ||
            !valid ||
            !hasUnsavedChanges();

        const saved = details && details.decision;
        const administratorId = Number(administratorInput.value);

        const alreadySent = Boolean(
            saved && (details.notifications || []).some(item =>
                Number(item.administrator_id) === administratorId &&
                Number(item.decision_version) === Number(saved.version)
            )
        );

        sendButton.disabled =
            busy ||
            !saved ||
            !administratorId ||
            hasUnsavedChanges() ||
            alreadySent;

        $("gc-notification-state").textContent = !saved
            ? "Save a program decision before sending a notification."
            : hasUnsavedChanges()
                ? "Save your changes before sending the decision."
                : !administratorId
                    ? "Select an Administrator to receive the email."
                    : alreadySent
                        ? "This decision version was already sent to this Administrator."
                        : "Ready to send the saved decision.";
    }

    function setBusy(value) {
        busy = value;
        updateButtons();

        administratorInput.disabled = value;
        decisionInput.disabled = value;
        rationaleInput.disabled = value;
        search.disabled = value;
    }

    function renderHistory(items) {
        const history = $("gc-notification-history");
        history.replaceChildren();

        if (!items || !items.length) {
            history.appendChild(
                element("p", "gc-muted", "No notifications sent.")
            );
            return;
        }

        items.forEach(item => {
            const row = element("div", "gc-history-entry");

            row.append(
                element("strong", "", item.recipient_email),
                element(
                    "span",
                    "",
                    `Version ${item.decision_version} · ${item.sent_at} UTC`
                )
            );

            history.appendChild(row);
        });
    }

    function renderDetails(data, keepRecipient = false) {
        details = data;

        detailContent.hidden = false;
        emptySelection.hidden = true;

        const app = data.application;

        $("gc-applicant-name").textContent = app.applicant_name;
        $("gc-program-name").textContent = app.degree_program;
        $("gc-term").textContent = app.term;
        $("gc-app-status").textContent = app.status;

        $("gc-view-application").href =
            `/advisor/application-review?application=${encodeURIComponent(app.id)}`;

        const completed = data.committee.completed;
        const assigned = data.committee.assigned;
        const pending = data.committee.pending;

        $("gc-review-progress").textContent =
            `${completed} of ${assigned} completed`;

        $("gc-progress-message").textContent = assigned === 0
            ? "No committee members have been assigned."
            : pending > 0
                ? `${pending} committee review${pending === 1 ? " is" : "s are"} still pending.`
                : "All assigned committee reviews have been completed.";

        decisionInput.value = data.decision
            ? data.decision.decision
            : "";

        rationaleInput.value = data.decision
            ? data.decision.rationale
            : "";

        if (!keepRecipient) {
            administratorInput.value = "";
        }

        renderHistory(data.notifications);
        updateButtons();
    }

    function updateSummary() {
        const item = applications.find(
            app => Number(app.id) === selectedId
        );

        if (!item || !details) return;

        item.decision = details.decision;
        item.notified = isSentForCurrentDecision();

        renderList();
    }

    async function selectApplication(id) {
        if (busy) return;

        selectedId = Number(id);
        const currentRequest = ++requestNumber;

        details = null;
        updateButtons();

        detailContent.hidden = true;
        emptySelection.hidden = false;

        emptySelection.querySelector("h2").textContent =
            "Loading application...";

        emptySelection.querySelector("p").textContent = "";

        renderList();

        feedback("gc-decision-feedback", "");
        feedback("gc-notify-feedback", "");

        try {
            const result = await api(
                `/api/graduate-college/applications/${selectedId}`
            );

            if (currentRequest !== requestNumber) return;

            renderDetails(result);

            const url = new URL(window.location.href);
            url.searchParams.set("application", selectedId);

            window.history.replaceState(null, "", url);

        } catch (error) {
            if (currentRequest !== requestNumber) return;

            emptySelection.querySelector("h2").textContent =
                "Unable to open application";

            emptySelection.querySelector("p").textContent =
                error.message;
        }
    }

    list.addEventListener("click", event => {
        const row = event.target.closest("[data-application-id]");

        if (row && !busy) {
            selectApplication(row.dataset.applicationId);
        }
    });

    search.addEventListener("input", renderList);
    decisionInput.addEventListener("change", updateButtons);
    rationaleInput.addEventListener("input", updateButtons);
    administratorInput.addEventListener("change", updateButtons);

    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (busy || !details || saveButton.disabled) return;

        setBusy(true);
        feedback("gc-decision-feedback", "Saving decision...");

        try {
            const result = await api(
                `/api/graduate-college/applications/${selectedId}/decision`,
                "PUT",
                {
                    decision: decisionInput.value,
                    rationale: rationaleInput.value.trim(),
                }
            );

            renderDetails(result, true);
            updateSummary();

            feedback(
                "gc-decision-feedback",
                "Program decision saved."
            );

        } catch (error) {
            feedback(
                "gc-decision-feedback",
                error.message,
                true
            );

        } finally {
            setBusy(false);
        }
    });

    sendButton.addEventListener("click", async () => {
        if (busy || !details || sendButton.disabled) return;

        const recipientId = Number(administratorInput.value);

        const recipientName =
            administratorInput.selectedOptions[0]?.textContent.trim() ||
            "the Administrator";

        const pending = details.committee.pending;

        const warning = pending > 0
            ? `\n\nNote: ${pending} committee review(s) are still pending.`
            : "";

        const confirmed = window.confirm(
            `Send the ${details.decision.decision} decision for ` +
            `${details.application.applicant_name} to ${recipientName}?` +
            warning
        );

        if (!confirmed) return;

        setBusy(true);
        feedback("gc-notify-feedback", "Sending notification...");

        try {
            const result = await api(
                `/api/graduate-college/applications/${selectedId}/notifications`,
                "POST",
                {
                    administrator_id: recipientId
                }
            );

            feedback(
                "gc-notify-feedback",
                `Notification sent to ${result.to}.`
            );

            try {
                const refreshed = await api(
                    `/api/graduate-college/applications/${selectedId}`
                );

                renderDetails(refreshed, true);
                updateSummary();

            } catch {
                feedback(
                    "gc-notify-feedback",
                    `Email accepted for ${result.to}. Refresh the page to check notification history.`
                );
            }

        } catch (error) {
            feedback(
                "gc-notify-feedback",
                error.message,
                true
            );

        } finally {
            setBusy(false);
        }
    });

    async function initialize() {
        try {
            const [apps, administrators] = await Promise.all([
                api("/api/graduate-college/applications"),
                api("/api/graduate-college/administrators"),
            ]);

            applications = apps;
            renderList();

            administrators.forEach(administrator => {
                const option = new Option(
                    `${administrator.name} (${administrator.email})`,
                    String(administrator.id)
                );

                administratorInput.add(option);
            });

            if (!applications.length) return;

            const requested = Number(
                new URLSearchParams(window.location.search)
                    .get("application")
            );

            const initial =
                applications.find(
                    item => Number(item.id) === requested
                ) || applications[0];

            selectApplication(initial.id);

        } catch (error) {
            notice(error.message);
        }
    }

    initialize();
});