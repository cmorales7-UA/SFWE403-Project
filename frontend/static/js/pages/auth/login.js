
document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".login-form");

    if (!form) {
        return;
    }

    const message = document.createElement("p");
    message.setAttribute("role", "alert");
    message.style.color = "#AB0520";
    form.appendChild(message);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        message.textContent = "";

        const username = form.querySelector(
            'input[name="username"]'
        ).value.trim();

        const password = form.querySelector(
            'input[name="password"]'
        ).value;

        const button = form.querySelector(
            'button[type="submit"]'
        );

        button.disabled = true;

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    typeof result.detail === "string"
                        ? result.detail
                        : "Unable to log in."
                );
            }

            const dashboards = {
                applicant: "/applicant",
                administrator: "/administrator",
                advisor: "/advisor",
                reviewer: "/reviewer",
                reference: "/reference",
                it_support: "/it-support"
            };

            const destination = dashboards[result.user_type];

            if (!destination) {
                throw new Error("Unknown account type.");
            }

            window.location.assign(destination);

        } catch (error) {
            message.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });
});
