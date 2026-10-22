(function () {
  var pageError = document.getElementById("page-error");
  var overallBox = document.getElementById("overall");
  var lowWarning = document.getElementById("low-warning");
  var subjectsBox = document.getElementById("subjects-box");
  var historyBox = document.getElementById("history-box");
  var correctionsBox = document.getElementById("corrections-box");
  var goalForm = document.getElementById("goal-form");
  var goalTarget = document.getElementById("goal-target");
  var goalFuture = document.getElementById("goal-future");
  var goalResult = document.getElementById("goal-result");
  var corrForm = document.getElementById("correction-form");
  var corrRecord = document.getElementById("corr-record");
  var corrStatus = document.getElementById("corr-status");
  var corrReason = document.getElementById("corr-reason");
  var corrError = document.getElementById("corr-error");

  function messageFor(result) {
    if (result.networkError) return "Cannot reach the server. Check that it is running.";
    if (result.data && typeof result.data.detail === "string") return result.data.detail;
    return "Something went wrong. Please try again.";
  }

  function show(el, text) {
    el.textContent = text;
    el.hidden = false;
  }

  function hide(el) {
    el.textContent = "";
    el.hidden = true;
  }

  function pct(value) {
    return value === null || value === undefined ? "No sessions yet" : value.toFixed(2) + "%";
  }

  async function loadSummary() {
    var r = await apiRequest("/student/summary");
    if (!r.ok) return show(pageError, messageFor(r));

    var o = r.data.overall;
    overallBox.textContent =
      "Overall: " + pct(o.percentage) + " (" + o.present + " of " + o.total + " classes attended)";
    if (o.low) {
      show(lowWarning, "Warning: your overall attendance is below " + o.threshold + "%.");
    } else {
      hide(lowWarning);
    }

    var rows = r.data.subjects.map(function (s) {
      return {
        subject_code: s.subject_code,
        subject_name: s.subject_name,
        present: s.present,
        total: s.total,
        percent_text: pct(s.percentage),
        flag: s.percentage === null ? "" : s.low ? "Low" : "OK",
      };
    });
    renderTable(
      subjectsBox,
      [
        { key: "subject_code", label: "Code" },
        { key: "subject_name", label: "Subject" },
        { key: "present", label: "Present" },
        { key: "total", label: "Total" },
        { key: "percent_text", label: "Attendance" },
        { key: "flag", label: "Status" },
      ],
      rows,
      "No finalized attendance yet."
    );
  }

  async function loadHistory() {
    var r = await apiRequest("/student/history");
    if (!r.ok) return show(pageError, messageFor(r));

    renderTable(
      historyBox,
      [
        { key: "session_date", label: "Date" },
        { key: "subject_code", label: "Subject" },
        { key: "status", label: "Status" },
      ],
      r.data,
      "No finalized classes yet."
    );

    // Fill the correction dropdown with this student's records.
    corrRecord.textContent = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent = r.data.length ? "Choose a class" : "No records to correct yet";
    corrRecord.appendChild(first);
    r.data.forEach(function (h) {
      var option = document.createElement("option");
      option.value = String(h.record_id);
      option.textContent = h.session_date + " – " + h.subject_code + " (" + h.status + ")";
      corrRecord.appendChild(option);
    });
  }

  async function loadCorrections() {
    var r = await apiRequest("/student/corrections");
    if (!r.ok) return show(pageError, messageFor(r));

    renderTable(
      correctionsBox,
      [
        { key: "session_date", label: "Date" },
        { key: "subject_code", label: "Subject" },
        { key: "current_status", label: "Recorded" },
        { key: "requested_status", label: "Requested" },
        { key: "status", label: "Decision" },
      ],
      r.data,
      "You have not requested any corrections."
    );
  }

  goalForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (goalTarget.value === "") {
      goalResult.textContent = "Enter a target percentage.";
      return;
    }
    var future = Number(goalFuture.value || 0);
    var query =
      "?target=" + encodeURIComponent(goalTarget.value) +
      "&future_classes=" + encodeURIComponent(future);
    var r = await apiRequest("/student/goal" + query);
    if (!r.ok) {
      goalResult.textContent = messageFor(r);
      return;
    }

    var g = r.data;
    var parts = ["Current attendance: " + pct(g.current_percentage) + "."];
    if (g.classes_needed === null) {
      parts.push("A " + g.target + "% target cannot be reached from here.");
    } else if (g.classes_needed === 0) {
      parts.push("You already meet the " + g.target + "% target.");
    } else {
      parts.push("Attend the next " + g.classes_needed + " classes in a row to reach " + g.target + "%.");
    }
    if (future > 0) {
      parts.push("If you attend all of the next " + future + " classes: " + pct(g.projected_percentage) + ".");
    }
    goalResult.textContent = parts.join(" ");
  });

  corrForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    hide(corrError);
    if (!corrRecord.value) return show(corrError, "Choose the class you want reviewed.");
    var reason = corrReason.value.trim();
    if (reason.length < 10) return show(corrError, "Explain the reason in at least 10 characters.");

    var r = await apiRequest("/student/corrections", {
      method: "POST",
      body: {
        attendance_record_id: Number(corrRecord.value),
        requested_status: corrStatus.value,
        reason: reason,
      },
    });
    if (r.ok) {
      showToast("Correction request sent to your teacher.", "success");
      corrReason.value = "";
      corrRecord.value = "";
      loadCorrections();
    } else {
      show(corrError, messageFor(r));
    }
  });

  document.getElementById("logout-btn").addEventListener("click", async function () {
    await apiRequest("/auth/logout", { method: "POST" });
    window.location.replace("/login");
  });

  apiRequest("/auth/me").then(async function (me) {
    if (!me.ok || !me.data || me.data.role !== "student") {
      window.location.replace("/login");
      return;
    }
    document.getElementById("student-name").textContent = me.data.full_name;
    await Promise.all([loadSummary(), loadHistory(), loadCorrections()]);
  });
})();