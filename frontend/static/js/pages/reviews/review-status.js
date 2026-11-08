document.addEventListener("DOMContentLoaded", () => {
  const page = document.getElementById("review-monitor-page");
  if (!page) return;

  const search = document.getElementById("rm-search");
  const programFilter = document.getElementById("rm-program");
  const statusFilter = document.getElementById("rm-status");
  const tableBody = document.getElementById("rm-table-body");
  const resultCount = document.getElementById("rm-result-count");
  const feedback = document.getElementById("rm-feedback");

  let assignments = [];
  let busy = false;
  let loaded = false;

  function create(tag, className = "", text = null) {
    const node = document.createElement(tag);

    if (className) node.className = className;
    if (text !== null) node.textContent = String(text);

    return node;
  }

  function cell(row, className = "") {
    const td = create("td", className);
    row.appendChild(td);
    return td;
  }

  function showFeedback(text, error = false) {
    feedback.textContent = text;
    feedback.dataset.state = error ? "error" : "success";
  }

  async function api(path, method = "GET") {
    let response;

    try {
      response = await fetch(path, {
        method,
        credentials: "same-origin",
      });
    } catch {
      throw new Error("Unable to connect to UA-GDAS.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : `Request failed (HTTP ${response.status}).`,
      );
    }

    return data;
  }

  function formatDate(value) {
    if (!value) return "Not set";

    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);

    if (!match) return String(value);

    const date = new Date(
      Number(match[1]),
      Number(match[2]) - 1,
      Number(match[3]),
    );

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function updateTotals() {
    const pending = assignments.filter(
      (item) => item.review_status === "Pending",
    );

    document.getElementById("rm-pending-count").textContent = pending.length;

    document.getElementById("rm-completed-count").textContent =
      assignments.length - pending.length;

    document.getElementById("rm-soon-count").textContent = pending.filter(
      (item) => item.application_status === "In Review" && item.due_soon,
    ).length;

    document.getElementById("rm-overdue-count").textContent = pending.filter(
      (item) => item.application_status === "In Review" && item.overdue,
    ).length;
  }

  function updatePrograms() {
    const previous = programFilter.value;

    const programs = [
      ...new Set(
        assignments.map((item) => item.degree_program).filter(Boolean),
      ),
    ].sort();

    programFilter.replaceChildren(new Option("All programs", ""));

    for (const program of programs) {
      programFilter.add(new Option(program, program));
    }

    if (programs.includes(previous)) {
      programFilter.value = previous;
    }
  }

  function filteredAssignments() {
    const query = search.value.trim().toLowerCase();

    return assignments.filter((item) => {
      const searchable = [
        item.applicant_name,
        item.reviewer_name,
        item.reviewer_email,
        item.degree_program,
        item.recommendation,
      ]
        .join(" ")
        .toLowerCase();

      if (query && !searchable.includes(query)) {
        return false;
      }

      if (programFilter.value && item.degree_program !== programFilter.value) {
        return false;
      }

      const active = item.application_status === "In Review";

      switch (statusFilter.value) {
        case "pending":
          return item.review_status === "Pending";

        case "completed":
          return item.review_status === "Completed";

        case "soon":
          return active && item.due_soon;

        case "overdue":
          return active && item.overdue;

        default:
          return true;
      }
    });
  }

  function addPerson(td, name, detail) {
    td.appendChild(create("strong", "rm-primary-text", name));

    if (detail) {
      td.appendChild(create("span", "rm-secondary-text", detail));
    }
  }

  function addRecommendation(td, item) {
    if (item.review_status === "Completed") {
      td.appendChild(
        create("span", "rm-primary-text", item.recommendation || "Completed"),
      );

      td.appendChild(create("span", "rm-secondary-text", "Reviewed"));

      return;
    }

    td.appendChild(create("span", "rm-tag rm-tag-neutral", "Pending"));
  }

  function addDeadline(td, item) {
    td.appendChild(
      create("span", "rm-primary-text", formatDate(item.due_date)),
    );

    if (item.review_status === "Completed") return;

    if (item.days_remaining === null || item.days_remaining === undefined) {
      return;
    }

    const days = Number(item.days_remaining);
    let description = "";
    let className = "rm-secondary-text";

    if (days < 0) {
      const count = Math.abs(days);
      description = `${count} day${count === 1 ? "" : "s"} overdue`;
      className += " rm-date-overdue";
    } else if (days === 0) {
      description = "Due today";
      className += " rm-date-warning";
    } else {
      description = `${days} day${days === 1 ? "" : "s"} left`;

      if (item.due_soon) {
        className += " rm-date-warning";
      }
    }

    td.appendChild(create("span", className, description));
  }

  function addReminderHistory(td, item) {
    if (!item.last_reminded_at) {
      td.appendChild(create("span", "rm-secondary-text", "Never"));
      return;
    }

    td.appendChild(
      create("span", "rm-primary-text", formatDate(item.last_reminded_at)),
    );

    if (item.reminder_count > 1) {
      td.appendChild(
        create("span", "rm-secondary-text", `${item.reminder_count} reminders`),
      );
    }
  }

  function addAction(td, item) {
    if (item.reminder_eligible) {
      const button = create("button", "rm-reminder-button", "Send Reminder");

      button.type = "button";
      button.dataset.assignmentId = item.assignment_id;
      button.disabled = busy;

      button.setAttribute(
        "aria-label",
        `Send reminder to ${item.reviewer_name} for ${item.applicant_name}`,
      );

      td.appendChild(button);
      return;
    }

    let label = "Unavailable";
    let className = "rm-action-text";

    if (item.review_status === "Completed") {
      label = "Reviewed";
    } else if (item.reminder_sent_today) {
      label = "Sent today";
      className += " rm-action-sent";
    } else if (item.days_remaining === null) {
      label = "No deadline";
    }

    td.appendChild(create("span", className, label));
  }

  function renderTable() {
    if (!loaded) return;

    const rows = filteredAssignments();
    tableBody.replaceChildren();

    resultCount.textContent = `${rows.length} of ${assignments.length} assignments`;

    if (!rows.length) {
      const tr = create("tr");
      const td = cell(tr, "rm-empty");

      td.colSpan = 6;
      td.textContent = assignments.length
        ? "No matching assignments."
        : "No review assignments found.";

      tableBody.appendChild(tr);
      return;
    }

    for (const item of rows) {
      const tr = create("tr");

      addPerson(cell(tr), item.applicant_name, item.degree_program);

      addPerson(cell(tr), item.reviewer_name, item.reviewer_email);

      addRecommendation(cell(tr), item);
      addDeadline(cell(tr), item);
      addReminderHistory(cell(tr), item);
      addAction(cell(tr, "rm-action-cell"), item);

      tableBody.appendChild(tr);
    }
  }

  async function loadAssignments() {
    if (busy) return;

    busy = true;

    try {
      const data = await api("/api/review-monitor/assignments");

      if (!Array.isArray(data)) {
        throw new Error("Invalid assignment data received.");
      }

      assignments = data;
      loaded = true;

      updatePrograms();
      updateTotals();
      showFeedback("");
    } catch (error) {
      showFeedback(error.message, true);

      if (!loaded) {
        resultCount.textContent = "Unable to load";
      }
    } finally {
      busy = false;
      renderTable();
    }
  }

  tableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-assignment-id]");

    if (!button || button.disabled || busy) return;

    const item = assignments.find(
      (assignment) =>
        String(assignment.assignment_id) === button.dataset.assignmentId,
    );

    if (!item || !item.reminder_eligible) return;

    const earlyNotice =
      item.days_remaining > 7
        ? `\n\nThe deadline is ${item.days_remaining} days away.`
        : "";

    const confirmed = window.confirm(
      `Send a review reminder now?\n\n` +
        `Reviewer: ${item.reviewer_name}\n` +
        `Applicant: ${item.applicant_name}\n` +
        `Deadline: ${formatDate(item.due_date)}` +
        earlyNotice,
    );

    if (!confirmed) return;

    busy = true;
    renderTable();

    showFeedback("Sending reminder...");

    try {
      await api(
        `/api/review-monitor/assignments/` +
          `${encodeURIComponent(item.assignment_id)}/reminders`,
        "POST",
      );

      item.reminder_eligible = false;
      item.reminder_sent_today = true;

      showFeedback(`Reminder sent to ${item.reviewer_email}.`);

      try {
        const updated = await api("/api/review-monitor/assignments");

        if (Array.isArray(updated)) {
          assignments = updated;
          updatePrograms();
          updateTotals();
        }
      } catch {
        showFeedback(
          "Reminder sent. The history will update when the page reloads.",
        );
      }
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      busy = false;
      renderTable();
    }
  });

  search.addEventListener("input", renderTable);
  programFilter.addEventListener("change", renderTable);
  statusFilter.addEventListener("change", renderTable);

  // Refresh data when returning to the browser tab.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && !busy) {
      loadAssignments();
    }
  });

  loadAssignments();
});
