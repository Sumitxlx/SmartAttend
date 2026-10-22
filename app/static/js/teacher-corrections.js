(function () {
  var pageError = document.getElementById("page-error");
  var tableBox = document.getElementById("table-box");

  var COLUMNS = [
    { key: "session_date", label: "Date" },
    { key: "subject_code", label: "Subject" },
    { key: "student_label", label: "Student" },
    { key: "current_status", label: "Recorded" },
    { key: "requested_status", label: "Requested" },
    { key: "reason", label: "Reason" },
  ];

  function messageFor(result) {
    if (result.networkError) return "Cannot reach the server. Check that it is running.";
    if (result.data && typeof result.data.detail === "string") return result.data.detail;
    return "Something went wrong. Please try again.";
  }

  function show(text) {
    pageError.textContent = text;
    pageError.hidden = false;
  }

  function hideError() {
    pageError.textContent = "";
    pageError.hidden = true;
  }

  async function decide(row, verb) {
    hideError();
    var r = await apiRequest("/teacher/corrections/" + row.id + "/" + verb, { method: "POST" });
    if (r.ok) {
      showToast(verb === "approve" ? "Approved. The record has been updated." : "Rejected. The record is unchanged.", "success");
      load();
    } else {
      show(messageFor(r));
    }
  }

  async function load() {
    var r = await apiRequest("/teacher/corrections/pending");
    if (!r.ok) {
      tableBox.textContent = "";
      return show(messageFor(r));
    }
    var rows = r.data.map(function (c) {
      return {
        id: c.id,
        session_date: c.session_date,
        subject_code: c.subject_code,
        student_label: c.student_name + " (" + c.roll_number + ")",
        current_status: c.current_status,
        requested_status: c.requested_status,
        reason: c.reason,
      };
    });
    renderTable(tableBox, COLUMNS, rows, "No correction requests are waiting for review.", [
      { label: "Approve", onClick: function (row) { decide(row, "approve"); } },
      { label: "Reject", onClick: function (row) { decide(row, "reject"); } },
    ]);
  }

  document.getElementById("logout-btn").addEventListener("click", async function () {
    await apiRequest("/auth/logout", { method: "POST" });
    window.location.replace("/login");
  });

  apiRequest("/auth/me").then(function (me) {
    if (!me.ok || !me.data || me.data.role !== "teacher") {
      window.location.replace("/login");
      return;
    }
    document.getElementById("teacher-name").textContent = me.data.full_name;
    load();
  });
})();