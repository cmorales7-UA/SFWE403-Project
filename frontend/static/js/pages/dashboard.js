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
// Preserve scroll position when selecting an application for review.
const reviewApplicationLinks = document.querySelectorAll(".review-application-item");
const dashboardMain = document.querySelector(".dashboard-main");

reviewApplicationLinks.forEach((link) => {
    link.addEventListener("click", () => {
        if (dashboardMain) {
            sessionStorage.setItem(
                "applicationReviewScroll",
                dashboardMain.scrollTop
            );
        }
    });
});


const savedReviewScroll = sessionStorage.getItem(
    "applicationReviewScroll"
);

const applicationSelected = new URLSearchParams(
    window.location.search
).has("application");


if (
    dashboardMain &&
    savedReviewScroll !== null &&
    applicationSelected
) {
    requestAnimationFrame(() => {
        dashboardMain.scrollTop = Number(savedReviewScroll);
        sessionStorage.removeItem("applicationReviewScroll");
    });
}