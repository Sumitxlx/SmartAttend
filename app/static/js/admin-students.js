(function () {
  var form = document.getElementById("student-form");
  var nameInput = document.getElementById("s-name");
  var emailInput = document.getElementById("s-email");
  var passwordInput = document.getElementById("s-password");
  var rollInput = document.getElementById("s-roll");
  var classSelect = document.getElementById("s-class");
  var filterSelect = document.getElementById("filter-class");
  var formError = document.getElementById("form-error");
  var saveBtn = document.getElementById("save-btn");
  var tableBox = document.getElementById("table-box");

  var departments = [];
  var classes = [];

  var COLUMNS = [
    { key: "roll_number", label: "Roll number" },
    { key: "full_name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "class_label", label: "Class" },
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

  function findById(list, id) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === id) return list[i];
    }
    return null;
  }

  function classLabel(cls) {
    if (!cls) return "Unknown class";
    var dept = findById(departments, cls.department_id);
    var code = dept ? dept.code : "?";
    return code + " " + cls.name + " (sem " + cls.semester + ", " + cls.academic_year + ")";
  }

  function fillSelect(select, items, labelFor, placeholder, includeAll) {
    select.textContent = "";
    if (includeAll) {
      var all = document.createElement("option");
      all.value = "";
      all.textContent = "All classes";
      select.appendChild(all);
    } else {
      var first = document.createElement("option");
      first.value = "";
      first.textContent = items.length ? placeholder : "No classes yet. Add one first.";
      select.appendChild(first);
    }
    items.forEach(function (item) {
      var option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = labelFor(item);
      select.appendChild(option);
    });
  }

  async function loadLookups() {
    var results = await Promise.all([
      apiRequest("/admin/departments"),
      apiRequest("/admin/classes"),
    ]);
    if (!results[0].ok || !results[1].ok) {
      showToast(messageFor(results[0].ok ? results[1] : results[0]), "error");
      return false;
    }
    departments = results[0].data;
    classes = results[1].data;

    fillSelect(classSelect, classes, classLabel, "Choose a class", false);
    fillSelect(filterSelect, classes, classLabel, "", true);
    return true;
  }

  async function load() {
    var query = filterSelect.value ? "?class_id=" + encodeURIComponent(filterSelect.value) : "";
    var result = await apiRequest("/admin/students" + query);
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }
    var rows = result.data.map(function (s) {
      return {
        roll_number: s.roll_number,
        full_name: s.full_name,
        email: s.email,
        class_label: classLabel(findById(classes, s.class_id)),
      };
    });
    renderTable(tableBox, COLUMNS, rows, "No students in this view yet.");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFormError();

    var payload = {
      full_name: nameInput.value.trim(),
      email: emailInput.value.trim(),
      password: passwordInput.value,
      roll_number: rollInput.value.trim(),
      class_id: Number(classSelect.value),
    };
    if (!payload.full_name || !payload.email || !payload.roll_number || !classSelect.value) {
      passwordInput.value = "";
      showFormError("Fill in every field and choose a class.");
      return;
    }

    saveBtn.disabled = true;
    var result = await apiRequest("/admin/students", { method: "POST", body: payload });
    saveBtn.disabled = false;
    passwordInput.value = "";

    if (result.ok) {
      showToast("Student added.", "success");
      nameInput.value = "";
      emailInput.value = "";
      rollInput.value = "";
      classSelect.value = "";
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  filterSelect.addEventListener("change", load);

  adminPageInit("students").then(async function (admin) {
    if (!admin) return;
    var ok = await loadLookups();
    if (ok) await load();
  });
})();