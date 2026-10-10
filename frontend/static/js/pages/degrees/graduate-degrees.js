document.addEventListener("DOMContentLoaded", () => {
    const degreeBrowser = document.querySelector(".degree-browser");

    if (!degreeBrowser) {
        return;
    }


    async function selectDegree(link) {
        try {
            const response = await fetch(link.href);

            if (!response.ok) {
                window.location.href = link.href;
                return;
            }

            const html = await response.text();

            const parser = new DOMParser();
            const newDocument = parser.parseFromString(
                html,
                "text/html"
            );

            const currentDetails = document.querySelector(
                ".degree-details-panel"
            );

            const newDetails = newDocument.querySelector(
                ".degree-details-panel"
            );

            if (!currentDetails || !newDetails) {
                window.location.href = link.href;
                return;
            }


            // Replace only the degree information panel.
            currentDetails.replaceWith(newDetails);


            // Update the selected item on the left.
            document.querySelectorAll(".degree-list-item").forEach(
                (item) => {
                    item.classList.remove("active");
                }
            );

            link.classList.add("active");


            // Update the URL without reloading the page.
            window.history.pushState(
                {},
                "",
                link.href
            );

        } catch (error) {
            window.location.href = link.href;
        }
    }


    degreeBrowser.addEventListener("click", (event) => {
        const link = event.target.closest(".degree-list-item");

        if (!link) {
            return;
        }

        event.preventDefault();

        selectDegree(link);
    });


    // Reload normally when using the browser Back or Forward buttons.
    window.addEventListener("popstate", () => {
        window.location.reload();
    });
});