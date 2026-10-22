(function () {
  var form = document.getElementById("class-form");
  var idInput = document.getElementById("class-id");
  var deptSelect = document.getElementById("class-dept");
  var nameInput = document.getElementById("class-name");
  var semesterInput = document.getElementById("class-semester");
  var yearInput = document.getElementById("class-year");
  var formTitle = document.getElementById("form-title");
  var formError = document.getElementById("form-error");
  var saveBtn = document.getElementById("save-btn");
  var cancelBtn = document.getElementById("cancel-btn");
  var tableBox = document.getElementById("table-box");

  var departments = [];

  var COLUMNS = [
    { key: "department_code", label: "Department" },
    { key: "name", label: "Class" },
    { key: "semester", label: "Semester" },
    { key: "academic_year", label: "Academic year" },
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
    nameInput.value = "";
    semesterInput.value = "";
    yearInput.value = "";
    formTitle.textContent = "Add a class";
    saveBtn.textContent = "Save";
    cancelBtn.hidden = true;
    clearFormError();
  }

  function startEdit(row) {
    idInput.value = String(row.id);
    deptSelect.value = String(row.department_id);
    nameInput.value = row.name;
    semesterInput.value = String(row.semester);
    yearInput.value = row.academic_year;
    formTitle.textContent = "Edit class " + row.name + " (semester " + row.semester + ")";
    saveBtn.textContent = "Update";
    cancelBtn.hidden = false;
    clearFormError();
    nameInput.focus();
  }

  async function remove(row) {
    var label = row.department_code + " " + row.name + " (semester " + row.semester + ", " + row.academic_year + ")";
    if (!window.confirm("Delete class " + label + "?")) return;
    var result = await apiRequest("/admin/classes/" + row.id, { method: "DELETE" });
    if (result.ok) {
      showToast("Class deleted.", "success");
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
    var result = await apiRequest("/admin/classes");
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }
    // The API returns department IDs; show the department code instead.
    var rows = result.data.map(function (c) {
      return {
        id: c.id,
        department_id: c.department_id,
        department_code: departmentCode(c.department_id),
        name: c.name,
        semester: c.semester,
        academic_year: c.academic_year,
      };
    });
    renderTable(tableBox, COLUMNS, rows, "No classes yet. Use the form above to add one.", [
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
      name: nameInput.value.trim(),
      department_id: Number(deptSelect.value),
      semester: Number(semesterInput.value),
      academic_year: yearInput.value.trim(),
    };
    if (!payload.name || !payload.semester || !payload.academic_year) {
      showFormError("Fill in the class name, semester and academic year.");
      return;
    }

    var id = idInput.value;
    saveBtn.disabled = true;
    var result = id
      ? await apiRequest("/admin/classes/" + id, { method: "PUT", body: payload })
      : await apiRequest("/admin/classes", { method: "POST", body: payload });
    saveBtn.disabled = false;

    if (result.ok) {
      showToast(id ? "Class updated." : "Class added.", "success");
      resetForm();
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  cancelBtn.addEventListener("click", resetForm);

  adminPageInit("classes").then(async function (admin) {
    if (!admin) return;
    await loadDepartments();
    await load();
  });
})();