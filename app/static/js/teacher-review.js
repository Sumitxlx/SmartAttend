(function () {
  var sessionInput = document.getElementById("session-id");
  var loadBtn = document.getElementById("load-btn");
  var pageError = document.getElementById("page-error");
  var summary = document.getElementById("summary");
  var tableBox = document.getElementById("table-box");
  var logoutBtn = document.getElementById("logout-btn");

  var sessionId = null;

  var COLUMNS = [
    { key: "roll_number", label: "Roll number" },
    { key: "full_name", label: "Name" },
    { key: "score_text", label: "Match score" },
  ];

  function messageFor(result) {
    if (result.networkError) return "Cannot reach the server. Check that it is running.";
    if (result.data && typeof result.data.detail === "string") return result.data.detail;
    return "Something went wrong. Please try again.";
  }

  function showError(text) {
    pageError.textContent = text;
    pageError.hidden = false;
  }

  function clearError() {
    pageError.textContent = "";
    pageError.hidden = true;
  }

  // Every change redraws from the server's list, so the screen never keeps its own copy.
  function render(rows) {
    summary.textContent = rows.length
      ? rows.length + " uncertain match(es) to review."
      : "No uncertain matches. You can finalize the session.";

    var tableRows = rows.map(function (r) {
      return {
        id: r.record_id,
        roll_number: r.roll_number,
        full_name: r.full_name,
        score_text: r.score === null ? "—" : r.score.toFixed(2),
      };
    });

    renderTable(tableBox, COLUMNS, tableRows, "No uncertain matches.", [
      { label: "Mark present", onClick: function (row) { resolve(row, "present"); } },
      { label: "Mark absent", onClick: function (row) { resolve(row, "absent"); } },
    ]);
  }

  async function load() {
    clearError();
    var raw = sessionInput.value.trim();
    if (!raw) {
      showError("Enter a session ID.");
      return;
    }
    sessionId = Number(raw);
    var r = await apiRequest("/teacher/sessions/" + sessionId + "/uncertain");
    if (r.ok) {
      render(r.data);
    } else {
      tableBox.textContent = "";
      summary.textContent = "";
      showError(messageFor(r));
    }
  }

  async function resolve(row, value) {
    clearError();
    var r = await apiRequest(
      "/teacher/sessions/" + sessionId + "/uncertain/" + row.id,
      { method: "PUT", body: { status: value } }
    );
    if (r.ok) {
      showToast("Saved as " + value + ".", "success");
      render(r.data);
    } else {
      showError(messageFor(r));
    }
  }

  loadBtn.addEventListener("click", load);
  sessionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") load();
  });

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