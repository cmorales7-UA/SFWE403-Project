// This section controls the dashboard sidebar.
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebarToggleIcon = document.getElementById("sidebar-toggle-icon");
const dashboardShell = document.getElementById("dashboard-shell");

if (sidebarToggle && sidebarToggleIcon && dashboardShell) {

    sidebarToggle.addEventListener("click", function () {

        dashboardShell.classList.toggle("sidebar-collapsed");

        const sidebarIsOpen =
            !dashboardShell.classList.contains("sidebar-collapsed");

        sidebarToggle.setAttribute(
            "aria-expanded",
            sidebarIsOpen
        );

        sidebarToggle.setAttribute(
            "aria-label",
            sidebarIsOpen
                ? "Collapse navigation"
                : "Expand navigation"
        );

        sidebarToggleIcon.textContent =
            sidebarIsOpen ? "‹" : "☰";

    });

}