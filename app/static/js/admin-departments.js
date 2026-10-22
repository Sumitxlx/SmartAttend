(function () {
  var form = document.getElementById("dept-form");
  var idInput = document.getElementById("dept-id");
  var codeInput = document.getElementById("dept-code");
  var nameInput = document.getElementById("dept-name");
  var formTitle = document.getElementById("form-title");
  var formError = document.getElementById("form-error");
  var saveBtn = document.getElementById("save-btn");
  var cancelBtn = document.getElementById("cancel-btn");
  var tableBox = document.getElementById("table-box");

  var COLUMNS = [
    { key: "code", label: "Code" },
    { key: "name", label: "Name" },
  ];

  // Turns an API response into a sentence a person can read.
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

  function resetForm() {
    idInput.value = "";
    codeInput.value = "";
    nameInput.value = "";
    formTitle.textContent = "Add a department";
    saveBtn.textContent = "Save";
    cancelBtn.hidden = true;
    clearFormError();
  }

  function startEdit(dept) {
    idInput.value = String(dept.id);
    codeInput.value = dept.code;
    nameInput.value = dept.name;
    formTitle.textContent = "Edit department " + dept.code;
    saveBtn.textContent = "Update";
    cancelBtn.hidden = false;
    clearFormError();
    codeInput.focus();
  }

  async function remove(dept) {
    if (!window.confirm("Delete department " + dept.code + "? This cannot be undone.")) return;
    var result = await apiRequest("/admin/departments/" + dept.id, { method: "DELETE" });
    if (result.ok) {
      showToast("Department deleted.", "success");
      if (idInput.value === String(dept.id)) resetForm();
      load();
    } else {
      showToast(messageFor(result), "error");
    }
  }

  async function load() {
    var result = await apiRequest("/admin/departments");
    if (!result.ok) {
      tableBox.textContent = "";
      showToast(messageFor(result), "error");
      return;
    }
    renderTable(
      tableBox,
      COLUMNS,
      result.data,
      "No departments yet. Use the form above to add one.",
      [
        { label: "Edit", onClick: startEdit },
        { label: "Delete", onClick: remove },
      ]
    );
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearFormError();

    var code = codeInput.value.trim();
    var name = nameInput.value.trim();
    if (!code || !name) {
      showFormError("Enter both a code and a name.");
      return;
    }

    var id = idInput.value;
    var body = { code: code, name: name };
    saveBtn.disabled = true;
    var result = id
      ? await apiRequest("/admin/departments/" + id, { method: "PUT", body: body })
      : await apiRequest("/admin/departments", { method: "POST", body: body });
    saveBtn.disabled = false;

    if (result.ok) {
      showToast(id ? "Department updated." : "Department added.", "success");
      resetForm();
      load();
    } else {
      showFormError(messageFor(result));
    }
  });

  cancelBtn.addEventListener("click", resetForm);

  adminPageInit("departments").then(function (admin) {
    if (admin) load();
  });
})();