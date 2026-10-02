// PocketSmart AI - JavaScript

document.addEventListener("DOMContentLoaded", function () {

    // Add a small confirmation before logging out
    const logoutLinks = document.querySelectorAll(
        'a[href="/logout"]'
    );

    logoutLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const confirmed = confirm(
                "Are you sure you want to logout?"
            );

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });


    // Prevent accidental multiple submissions
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {

        form.addEventListener("submit", function () {

            const button = form.querySelector(
                'button[type="submit"]'
            );

            if (button) {
                button.disabled = true;
                button.innerText = "Generating...";
            }

        });

    });

});