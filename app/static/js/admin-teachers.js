(function () {
  var form = document.getElementById("teacher-form");
  var nameInput = document.getElementById("t-name");
  var emailInput = document.getElementById("t-email");
  var passwordInput = document.getElementById("t-password");
  var employeeInput = document.getElementById("t-employee");
  var deptSelect = document.getElementById("t-dept");
  var formError = document.getElementById("form-error");
  var saveBtn = document.getElementById("save-btn");
  var tableBox = document.getElementById("table-box");

  var departments = [];

  var COLUMNS = [
    { key: "full_name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "employee_id", label: "Employee ID" },
    { key: "department_code", label: "Department" },
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
    var result = await apiRequest("/admin/teachers");
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }
    var rows = result.data.map(function (t) {
      return {
        full_name: t.full_name,
        email: t.email,
        employee_id: t.employee_id,
        department_code: departmentCode(t.department_id),
      };
    });
    renderTable(tableBox, COLUMNS, rows, "No teachers yet. Use the form above to add one.");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFormError();

    var payload = {
      full_name: nameInput.value.trim(),
      email: emailInput.value.trim(),
      password: passwordInput.value,
      employee_id: employeeInput.value.trim(),
      department_id: Number(deptSelect.value),
    };
    if (!payload.full_name || !payload.email || !payload.employee_id || !deptSelect.value) {
      passwordInput.value = "";
      showFormError("Fill in every field and choose a department.");
      return;
    }

    saveBtn.disabled = true;
    var result = await apiRequest("/admin/teachers", { method: "POST", body: payload });
    saveBtn.disabled = false;
    // Clear the password whether or not the request succeeded.
    passwordInput.value = "";

    if (result.ok) {
      showToast("Teacher added.", "success");
      nameInput.value = "";
      emailInput.value = "";
      employeeInput.value = "";
      deptSelect.value = "";
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  adminPageInit("teachers").then(async function (admin) {
    if (!admin) return;
    await loadDepartments();
    await load();
  });
})();