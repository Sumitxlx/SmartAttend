(function () {
  var form = document.getElementById("assign-form");
  var teacherSelect = document.getElementById("assign-teacher");
  var subjectSelect = document.getElementById("assign-subject");
  var classSelect = document.getElementById("assign-class");
  var formError = document.getElementById("form-error");
  var setupNote = document.getElementById("setup-note");
  var saveBtn = document.getElementById("save-btn");
  var tableBox = document.getElementById("table-box");

  // Lookup data, loaded once and used to show names instead of IDs.
  var teachers = [];
  var subjects = [];
  var classes = [];
  var departments = [];

  var COLUMNS = [
    { key: "teacher", label: "Teacher" },
    { key: "subject", label: "Subject" },
    { key: "class", label: "Class" },
  ];

  function messageFor(result) {
    if (result.networkError) return "Cannot reach the server. Check that it is running.";
    if (result.data && typeof result.data.detail === "string") return result.data.detail;
    return "Please check the form and try again.";
  }

  function showFormError(text) {
    formError.textContent = text;
    formError.hidden = false;
  }

  function clearFormError() {
    formError.textContent = "";
    formError.hidden = true;
  }

  function fillSelect(select, items, labelFor, placeholder) {
    select.textContent = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent = items.length ? placeholder : "None available";
    select.appendChild(first);
    items.forEach(function (item) {
      var option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = labelFor(item);
      select.appendChild(option);
    });
  }

  function findById(list, id) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === id) return list[i];
    }
    return null;
  }

  function deptCode(id) {
    var d = findById(departments, id);
    return d ? d.code : "?";
  }

  // Shows a helpful note when something needed for assignments is missing.
  function updateSetupNote() {
    var missing = [];
    if (!teachers.length) missing.push("teachers (add them through the API for now; the Teachers screen comes in 6d)");
    if (!subjects.length) missing.push("subjects (add them on the Subjects page)");
    if (!classes.length) missing.push("classes (add them on the Classes page)");

    if (missing.length) {
      setupNote.textContent = "You need " + missing.join(", ") + " before you can make an assignment.";
      setupNote.hidden = false;
    } else {
      setupNote.textContent = "";
      setupNote.hidden = true;
    }
    saveBtn.disabled = !(teachers.length && subjects.length && classes.length);
  }

  async function remove(row) {
    if (!window.confirm("Remove " + row.teacher + " from " + row.subject + " in " + row["class"] + "?")) return;
    var result = await apiRequest("/admin/teaching-assignments/" + row.id, { method: "DELETE" });
    if (result.ok) {
      showToast("Assignment removed.", "success");
      load();
    } else {
      showToast(messageFor(result), "error");
    }
  }

  async function loadLookups() {
    var results = await Promise.all([
      apiRequest("/admin/departments"),
      apiRequest("/admin/subjects"),
      apiRequest("/admin/classes"),
      apiRequest("/admin/teachers"),
    ]);
    var failed = results.find(function (r) { return !r.ok; });
    if (failed) {
      showToast(messageFor(failed), "error");
      return false;
    }

    departments = results[0].data;
    subjects = results[1].data;
    classes = results[2].data;
    teachers = results[3].data;

    fillSelect(teacherSelect, teachers, function (t) {
      return t.full_name + " (" + t.employee_id + ", " + deptCode(t.department_id) + ")";
    }, "Choose a teacher");
    fillSelect(subjectSelect, subjects, function (s) {
      return s.code + " – " + s.name + " (sem " + s.semester + ")";
    }, "Choose a subject");
    fillSelect(classSelect, classes, function (c) {
      return deptCode(c.department_id) + " " + c.name + " (sem " + c.semester + ", " + c.academic_year + ")";
    }, "Choose a class");

    updateSetupNote();
    return true;
  }

  async function load() {
    var ok = await loadLookups();
    if (!ok) return;

    var result = await apiRequest("/admin/teaching-assignments");
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }

    var rows = result.data.map(function (a) {
      var teacher = findById(teachers, a.teacher_id);
      var subject = findById(subjects, a.subject_id);
      var cls = findById(classes, a.class_id);
      return {
        id: a.id,
        teacher: teacher ? teacher.full_name : "Unknown teacher",
        subject: subject ? subject.code + " " + subject.name : "Unknown subject",
        class: cls ? deptCode(cls.department_id) + " " + cls.name + " (sem " + cls.semester + ")" : "Unknown class",
      };
    });

    renderTable(tableBox, COLUMNS, rows, "No assignments yet.", [
      { label: "Remove", onClick: remove },
    ]);
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFormError();

    if (!teacherSelect.value || !subjectSelect.value || !classSelect.value) {
      showFormError("Choose a teacher, a subject and a class.");
      return;
    }

    saveBtn.disabled = true;
    var result = await apiRequest("/admin/teaching-assignments", {
      method: "POST",
      body: {
        teacher_id: Number(teacherSelect.value),
        subject_id: Number(subjectSelect.value),
        class_id: Number(classSelect.value),
      },
    });
    saveBtn.disabled = false;

    if (result.ok) {
      showToast("Assignment created.", "success");
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  adminPageInit("assignments").then(async function (admin) {
    if (admin) await load();
  });
})();