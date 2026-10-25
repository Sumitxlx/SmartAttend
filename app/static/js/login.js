(function () {
  var title = document.getElementById("page-title");
  var pageError = document.getElementById("page-error");
  var checking = document.getElementById("checking");
  var form = document.getElementById("login-form");
  var signedIn = document.getElementById("signed-in");
  var emailInput = document.getElementById("email");
  var passwordInput = document.getElementById("password");
  var submitButton = document.getElementById("submit-btn");
  var logoutButton = document.getElementById("logout-btn");

  // Where each role goes after signing in.
  var HOME_BY_ROLE = {
    admin: "/admin",
    teacher: "/teach/home",
    student: "/portal/student",
  };

  function showView(name) {
    checking.hidden = name !== "checking";
    form.hidden = name !== "form";
    signedIn.hidden = name !== "signed-in";
    title.textContent = name === "signed-in" ? "Signed in" : "Sign in";
  }

  function showError(message) {
    pageError.textContent = message;
    pageError.hidden = false;
  }

  function clearError() {
    pageError.textContent = "";
    pageError.hidden = true;
  }

  function renderUser(user) {
    var home = HOME_BY_ROLE[user.role];
    if (home) {
      window.location.replace(home);
      return;
    }
    // Unknown role: show the signed-in box as before.
    document.getElementById("user-name").textContent = user.full_name;
    document.getElementById("user-email").textContent = user.email;
    document.getElementById("user-role").textContent = user.role;
    showView("signed-in");
  }

  function setBusy(isBusy) {
    submitButton.disabled = isBusy;
    submitButton.textContent = isBusy ? "Signing in…" : "Sign in";
  }

  async function checkSession() {
    var result = await apiRequest("/auth/me");
    if (result.ok) {
      renderUser(result.data);
      return;
    }
    showView("form");
    if (result.networkError) {
      showError("Cannot reach the server. Check that it is running, then reload the page.");
    } else if (result.status !== 401) {
      showError("Could not check your session. Please reload the page.");
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearError();

    var email = emailInput.value.trim();
    var password = passwordInput.value;
    if (!email || !password) {
      showError("Enter both your email and your password.");
      (email ? passwordInput : emailInput).focus();
      return;
    }

    setBusy(true);
    var result = await apiRequest("/auth/login", {
      method: "POST",
      body: { email: email, password: password },
    });
    setBusy(false);
    passwordInput.value = "";

    if (result.ok) {
      renderUser(result.data);
    } else if (result.networkError) {
      showError("Cannot reach the server. Check your connection and try again.");
    } else if (result.status === 401) {
      showError("Incorrect email or password.");
      passwordInput.focus();
    } else if (result.status === 422) {
      showError("Enter a valid email address and password.");
    } else {
      showError("Something went wrong. Please try again.");
    }
  });

  logoutButton.addEventListener("click", async function () {
    clearError();
    var result = await apiRequest("/auth/logout", { method: "POST" });
    if (!result.ok) {
      showError("Could not sign out. Please try again.");
      return;
    }
    emailInput.value = "";
    passwordInput.value = "";
    showView("form");
    emailInput.focus();
  });

  checkSession();
})();