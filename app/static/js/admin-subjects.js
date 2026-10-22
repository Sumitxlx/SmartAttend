(function () {
  var form = document.getElementById("subject-form");
  var idInput = document.getElementById("subject-id");
  var deptSelect = document.getElementById("subject-dept");
  var codeInput = document.getElementById("subject-code");
  var nameInput = document.getElementById("subject-name");
  var semesterInput = document.getElementById("subject-semester");
  var formTitle = document.getElementById("form-title");
  var formError = document.getElementById("form-error");
  var saveBtn = document.getElementById("save-btn");
  var cancelBtn = document.getElementById("cancel-btn");
  var tableBox = document.getElementById("table-box");

  var departments = [];

  var COLUMNS = [
    { key: "code", label: "Code" },
    { key: "name", label: "Subject" },
    { key: "department_code", label: "Department" },
    { key: "semester", label: "Semester" },
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

  function departmentCode(id) {
    for (var i = 0; i < departments.length; i++) {
      if (departments[i].id === id) return departments[i].code;
    }
    return "?";
  }

  function fillDepartmentOptions() {
    deptSelect.textContent = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent = departments.length ? "Choose a department" : "No departments yet. Add one first.";
    deptSelect.appendChild(first);
    departments.forEach(function (d) {
      var option = document.createElement("option");
      option.value = String(d.id);
      option.textContent = d.code + " – " + d.name;
      deptSelect.appendChild(option);
    });
  }

  function resetForm() {
    idInput.value = "";
    deptSelect.value = "";
    codeInput.value = "";
    nameInput.value = "";
    semesterInput.value = "";
    formTitle.textContent = "Add a subject";
    saveBtn.textContent = "Save";
    cancelBtn.hidden = true;
    clearFormError();
  }

  function startEdit(row) {
    idInput.value = String(row.id);
    deptSelect.value = String(row.department_id);
    codeInput.value = row.code;
    nameInput.value = row.name;
    semesterInput.value = String(row.semester);
    formTitle.textContent = "Edit subject " + row.code;
    saveBtn.textContent = "Update";
    cancelBtn.hidden = false;
    clearFormError();
    codeInput.focus();
  }

  async function remove(row) {
    if (!window.confirm("Delete subject " + row.code + " (" + row.name + ")?")) return;
    var result = await apiRequest("/admin/subjects/" + row.id, { method: "DELETE" });
    if (result.ok) {
      showToast("Subject deleted.", "success");
      if (idInput.value === String(row.id)) resetForm();
      load();
    } else {
      showToast(messageFor(result), "error");
    }
  }

  async function loadDepartments() {
    var result = await apiRequest("/admin/departments");
    if (!result.ok) {
      showToast(messageFor(result), "error");
      return;
    }
    departments = result.data;
    fillDepartmentOptions();
  }

  async function load() {
    var result = await apiRequest("/admin/subjects");
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }
    var rows = result.data.map(function (s) {
      return {
        id: s.id,
        department_id: s.department_id,
        code: s.code,
        name: s.name,
        department_code: departmentCode(s.department_id),
        semester: s.semester,
      };
    });
    renderTable(tableBox, COLUMNS, rows, "No subjects yet. Use the form above to add one.", [
      { label: "Edit", onClick: startEdit },
      { label: "Delete", onClick: remove },
    ]);
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFormError();

    if (!deptSelect.value) {
      showFormError("Choose a department.");
      return;
    }
    var payload = {
      code: codeInput.value.trim(),
      name: nameInput.value.trim(),
      department_id: Number(deptSelect.value),
      semester: Number(semesterInput.value),
    };
    if (!payload.code || !payload.name || !payload.semester) {
      showFormError("Fill in the code, name and semester.");
      return;
    }

    var id = idInput.value;
    saveBtn.disabled = true;
    var result = id
      ? await apiRequest("/admin/subjects/" + id, { method: "PUT", body: payload })
      : await apiRequest("/admin/subjects", { method: "POST", body: payload });
    saveBtn.disabled = false;

    if (result.ok) {
      showToast(id ? "Subject updated." : "Subject added.", "success");
      resetForm();
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  cancelBtn.addEventListener("click", resetForm);

  adminPageInit("subjects").then(async function (admin) {
    if (!admin) return;
    await loadDepartments();
    await load();
  });
})();