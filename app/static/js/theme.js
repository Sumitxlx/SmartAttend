// Loaded in <head> so the saved theme is applied before the page is drawn (no flash).
(function () {
  var KEY = "smartattend-theme";

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  function save(value) {
    try {
      localStorage.setItem(KEY, value);
    } catch (e) {
      /* storage blocked: the theme simply won't persist */
    }
  }

  function preferred() {
    var saved = stored();
    if (saved === "light" || saved === "dark") return saved;
    var darkOs = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return darkOs ? "dark" : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  apply(preferred());

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme-toggle");
    if (!button) return;

    function updateLabel() {
      var isDark = document.documentElement.getAttribute("data-theme") === "dark";
      button.textContent = isDark ? "Light theme" : "Dark theme";
    }

    updateLabel();
    button.addEventListener("click", function () {
      var isDark = document.documentElement.getAttribute("data-theme") === "dark";
      var next = isDark ? "light" : "dark";
      apply(next);
      save(next);
      updateLabel();
    });
  });
})();