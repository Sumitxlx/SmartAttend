(function () {
  var logoutBtn = document.getElementById("logout-btn");

  logoutBtn.addEventListener("click", async function () {
    await apiRequest("/auth/logout", { method: "POST" });
    window.location.replace("/login");
  });

  apiRequest("/auth/me").then(function (me) {
    if (!me.ok || !me.data || me.data.role !== "teacher") {
      window.location.replace("/login");
      return;
    }
    document.getElementById("teacher-name").textContent = me.data.full_name;
  });
})();