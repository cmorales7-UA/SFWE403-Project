document.addEventListener("DOMContentLoaded", () => {
    const newPassword = document.getElementById(
        "new_password"
    );

    const confirmPassword = document.getElementById(
        "confirm_new_password"
    );


    function validatePasswordMatch() {
        if (
            confirmPassword.value &&
            newPassword.value !== confirmPassword.value
        ) {
            confirmPassword.setCustomValidity(
                "Passwords do not match."
            );
        } else {
            confirmPassword.setCustomValidity("");
        }
    }


    newPassword.addEventListener(
        "input",
        validatePasswordMatch
    );

    confirmPassword.addEventListener(
        "input",
        validatePasswordMatch
    );
});