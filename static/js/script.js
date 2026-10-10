// Foodie Hub global client-side helpers
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".flash").forEach(function (el) {
        setTimeout(function () {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
        }, 3000);
    });
});
