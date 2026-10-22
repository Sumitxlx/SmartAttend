(function () {
  var assignmentSelect = document.getElementById("assignment");
  var startBtn = document.getElementById("start-btn");
  var finalizeBtn = document.getElementById("finalize-btn");
  var statusLine = document.getElementById("session-status");
  var pageError = document.getElementById("page-error");
  var sessionPanel = document.getElementById("session-panel");
  var summary = document.getElementById("summary");
  var tableBox = document.getElementById("table-box");
  var logoutBtn = document.getElementById("logout-btn");

  var session = null;

  var COLUMNS = [
    { key: "roll_number", label: "Roll number" },
    { key: "full_name", label: "Name" },
    { key: "status_label", label: "Status" },
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

  function statusLabel(status) {
    if (status === "present") return "Present";
    if (status === "absent") return "Absent";
    return "Not marked";
  }

  function hideSession() {
    session = null;
    sessionPanel.hidden = true;
    tableBox.textContent = "";
    summary.textContent = "";
    startBtn.hidden = true;
    finalizeBtn.hidden = true;
  }

  // Draws the session from a SessionOut response. Every change goes through here,
  // so the screen always shows what the server stored.
  function render(s) {
    session = s;
    startBtn.hidden = true;
    statusLine.textContent = "";

    var marked = s.students.filter(function (st) { return st.status !== null; }).length;
    var locked = s.status === "finalized";
    summary.textContent =
      (locked ? "Finalized. " : "Session active. ") +
      "Marked " + marked + " of " + s.students.length + " students.";

    finalizeBtn.hidden = locked;
    sessionPanel.hidden = false;

    var rows = s.students.map(function (st) {
      return {
        student_id: st.student_id,
        roll_number: st.roll_number,
        full_name: st.full_name,
        status_label: statusLabel(st.status),
      };
    });

    // Once finalized, no action buttons are passed, so the table becomes read-only.
    renderTable(
      tableBox,
      COLUMNS,
      rows,
      "No students are enrolled in this class.",
      locked
        ? null
        : [
            { label: "Present", onClick: function (row) { mark(row, "present"); } },
            { label: "Absent", onClick: function (row) { mark(row, "absent"); } },
          ]
    );
  }

  async function mark(row, value) {
    if (!session) return;
    clearError();
    var result = await apiRequest(
      "/teacher/sessions/" + session.id + "/students/" + row.student_id,
      { method: "PUT", body: { status: value } }
    );
    if (result.ok) {
      render(result.data);
    } else {
      showError(messageFor(result));
    }
  }

  // Looks for a session already started today for the chosen assignment.
  async function loadToday() {
    clearError();
    hideSession();
    statusLine.textContent = "";
    if (!assignmentSelect.value) return;

    var result = await apiRequest("/teacher/assignments/" + assignmentSelect.value + "/today");
    if (result.ok) {
      render(result.data);
    } else if (result.status === 404) {
      statusLine.textContent = "No session has been started for this class today.";
      startBtn.hidden = false;
    } else {
      showError(messageFor(result));
    }
  }

  async function loadAssignments() {
    var result = await apiRequest("/teacher/assignments");
    if (!result.ok) {
      showError(messageFor(result));
      return;
    }

    assignmentSelect.textContent = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent = result.data.length ? "Choose an assignment" : "You have no assignments yet.";
    assignmentSelect.appendChild(first);

    result.data.forEach(function (a) {
      var option = document.createElement("option");
      option.value = String(a.id);
      option.textContent =
        a.subject_code + " " + a.subject_name + " – Class " + a.class_name +
        " (sem " + a.semester + ", " + a.academic_year + ")";
      assignmentSelect.appendChild(option);
    });
  }

  assignmentSelect.addEventListener("change", loadToday);

  startBtn.addEventListener("click", async function () {
    clearError();
    startBtn.disabled = true;
    var result = await apiRequest("/teacher/sessions", {
      method: "POST",
      body: { teaching_assignment_id: Number(assignmentSelect.value) },
    });
    startBtn.disabled = false;

    if (result.ok) {
      showToast("Session started.", "success");
      render(result.data);
    } else {
      showError(messageFor(result));
    }
  });

  finalizeBtn.addEventListener("click", async function () {
    if (!session) return;
    var unmarked = session.students.filter(function (st) { return st.status === null; }).length;
    var question = unmarked
      ? unmarked + " student(s) are not marked and will be recorded as absent. Finalizing locks the session. Continue?"
      : "Finalizing locks the session and cannot be undone here. Continue?";
    if (!window.confirm(question)) return;

    clearError();
    finalizeBtn.disabled = true;
    var result = await apiRequest("/teacher/sessions/" + session.id + "/finalize", { method: "POST" });
    finalizeBtn.disabled = false;

    if (result.ok) {
      showToast("Session finalized. " + result.data.auto_marked_absent + " marked absent.", "success");
      render(result.data.session);
    } else {
      showError(messageFor(result));
    }
  });

  logoutBtn.addEventListener("click", async function () {
    await apiRequest("/auth/logout", { method: "POST" });
    window.location.replace("/login");
  });

  // Only teachers may use this page. The backend enforces this too.
  apiRequest("/auth/me").then(async function (me) {
    if (!me.ok || !me.data || me.data.role !== "teacher") {
      window.location.replace("/login");
      return;
    }
    document.getElementById("teacher-name").textContent = me.data.full_name;
    await loadAssignments();
  });
})();