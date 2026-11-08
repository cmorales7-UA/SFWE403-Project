document.addEventListener("DOMContentLoaded", () => {
    const applicationId = Number(
        new URLSearchParams(window.location.search).get("application")
    );

    const reviewForm = document.querySelector(".review-form");
    const messageForm = document.querySelector(".review-message-form");

    if (!applicationId || !reviewForm || !messageForm) {
        return;
    }

    const comments = reviewForm.querySelector('[name="review_comments"]');
    const recommendation = reviewForm.querySelector('[name="recommendation"]');
    const reviewButton = reviewForm.querySelector('button[type="submit"]');

    const messageInput = messageForm.querySelector('[name="message"]');
    const messageButton = messageForm.querySelector('button[type="submit"]');
    const messageHistory = document.querySelector(".review-message-history");

    const reviewFeedback = document.createElement("p");
    const messageFeedback = document.createElement("p");

    reviewFeedback.className = "review-feedback";
    messageFeedback.className = "review-feedback";

    reviewFeedback.setAttribute("role", "status");
    reviewFeedback.setAttribute("aria-live", "polite");

    messageFeedback.setAttribute("role", "status");
    messageFeedback.setAttribute("aria-live", "polite");

    reviewForm.appendChild(reviewFeedback);
    messageForm.appendChild(messageFeedback);

    function showFeedback(element, text, isError = false) {
        element.textContent = text;
        element.style.color = isError ? "#AB0520" : "#216647";
    }

    async function request(path, method = "GET", payload = null) {
        const options = {
            method,
            credentials: "same-origin",
            headers: {}
        };

        if (payload !== null) {
            options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(payload);
        }

        let response;

        try {
            response = await fetch(path, options);
        } catch {
            throw new Error(
                "Unable to connect to UA-GDAS. Check the server connection."
            );
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = data.detail;

            const error = typeof detail === "string"
                ? detail
                : Array.isArray(detail)
                    ? detail.map(item => item.msg).join("; ")
                    : `Request failed (HTTP ${response.status}).`;

            throw new Error(error);
        }

        return data;
    }

    function updateListStatuses(statuses) {
        const links = document.querySelectorAll(
            ".review-application-item"
        );

        links.forEach(link => {
            const url = new URL(link.href);
            const id = url.searchParams.get("application");
            const status = link.querySelector(".review-progress");

            if (!status) return;

            const reviewed = Boolean(statuses[id]);

            status.textContent = reviewed ? "Reviewed" : "Pending";
            status.classList.toggle(
                "review-progress-complete",
                reviewed
            );
        });
    }

    function renderMessages(messages) {
        if (!messageHistory) return;

        messageHistory.replaceChildren();

        if (!messages.length) {
            const empty = document.createElement("p");
            empty.className = "review-unavailable";
            empty.textContent = "No messages for this application.";

            messageHistory.appendChild(empty);
            return;
        }

        messages.forEach(item => {
            const article = document.createElement("article");
            article.className = "review-message";

            const heading = document.createElement("div");
            heading.className = "review-message-heading";

            const sender = document.createElement("strong");
            sender.textContent = item.sender_name;

            const time = document.createElement("span");
            time.textContent = item.timestamp || "";

            const body = document.createElement("p");
            body.textContent = item.content;

            heading.append(sender, time);
            article.append(heading, body);
            messageHistory.appendChild(article);
        });
    }

    async function loadReview() {
        const data = await request(
            `/api/reviewer/applications/${applicationId}/review`
        );

        comments.value = data.comments || "";
        recommendation.value = data.recommendation || "";

        renderMessages(data.messages || []);
    }

    async function loadStatuses() {
        const statuses = await request("/api/reviewer/reviews");
        updateListStatuses(statuses);
    }

    reviewForm.addEventListener("submit", async event => {
        event.preventDefault();

        if (!recommendation.value) {
            showFeedback(
                reviewFeedback,
                "Select a recommendation before submitting.",
                true
            );
            return;
        }

        reviewButton.disabled = true;
        showFeedback(reviewFeedback, "Saving recommendation...");

        try {
            await request(
                `/api/reviewer/applications/${applicationId}/recommendation`,
                "POST",
                {
                    recommendation: recommendation.value,
                    comments: comments.value
                }
            );

            showFeedback(
                reviewFeedback,
                "Recommendation saved successfully."
            );

            await loadStatuses();
        } catch (error) {
            showFeedback(reviewFeedback, error.message, true);
        } finally {
            reviewButton.disabled = false;
        }
    });

    messageForm.addEventListener("submit", async event => {
        event.preventDefault();

        const text = messageInput.value.trim();

        if (!text) {
            showFeedback(
                messageFeedback,
                "Enter a message before sending.",
                true
            );
            return;
        }

        if (!window.confirm("Send this message to the assigned Advisor?")) {
            return;
        }

        messageButton.disabled = true;
        showFeedback(messageFeedback, "Sending message...");

        try {
            const result = await request(
                `/api/reviewer/applications/${applicationId}/messages`,
                "POST",
                { message: text }
            );

            messageInput.value = "";

            showFeedback(
                messageFeedback,
                `Message sent to ${result.to}.`
            );

            await loadReview();
        } catch (error) {
            showFeedback(messageFeedback, error.message, true);
        } finally {
            messageButton.disabled = false;
        }
    });

    loadReview().catch(error => {
        showFeedback(reviewFeedback, error.message, true);
    });

    loadStatuses().catch(error => {
        showFeedback(reviewFeedback, error.message, true);
    });
});