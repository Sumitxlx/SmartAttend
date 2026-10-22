(function () {
  var sessionInput = document.getElementById("session-id");
  var cameraBtn = document.getElementById("camera-btn");
  var captureBtn = document.getElementById("capture-btn");
  var preview = document.getElementById("preview");
  var canvas = document.getElementById("snapshot");
  var pageError = document.getElementById("page-error");
  var summary = document.getElementById("summary");
  var rawBox = document.getElementById("raw");
  var logoutBtn = document.getElementById("logout-btn");

  var stream = null;

  function showError(text) {
    pageError.textContent = text;
    pageError.hidden = false;
  }

  function clearError() {
    pageError.textContent = "";
    pageError.hidden = true;
  }

  function messageFor(result) {
    if (result.networkError) return "Cannot reach the server. Check that it is running.";
    if (result.data && typeof result.data.detail === "string") return result.data.detail;
    return "Something went wrong. Please try again.";
  }

  cameraBtn.addEventListener("click", async function () {
    clearError();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError("This browser cannot access the camera. Try Chrome on http://127.0.0.1:8000.");
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      preview.srcObject = stream;
      preview.hidden = false;
      captureBtn.disabled = false;
      cameraBtn.textContent = "Camera on";
    } catch (e) {
      showError("Camera permission was refused or no camera was found: " + e.name);
    }
  });

  captureBtn.addEventListener("click", function () {
    clearError();
    var sessionId = sessionInput.value.trim();
    if (!sessionId) {
      showError("Enter the active session ID first.");
      return;
    }
    if (!preview.videoWidth) {
      showError("The camera is not ready yet. Wait a moment and try again.");
      return;
    }

    canvas.width = preview.videoWidth;
    canvas.height = preview.videoHeight;
    canvas.getContext("2d").drawImage(preview, 0, 0);

    canvas.toBlob(async function (blob) {
      if (!blob) {
        showError("Could not capture the frame.");
        return;
      }
      captureBtn.disabled = true;
      summary.textContent = "Sending the frame to the server…";

      var form = new FormData();
      form.append("photo", blob, "frame.jpg");

      var started = performance.now();
      var response;
      try {
        response = await fetch("/teacher/sessions/" + encodeURIComponent(sessionId) + "/recognize", {
          method: "POST",
          body: form,
          credentials: "same-origin",
        });
      } catch (e) {
        captureBtn.disabled = false;
        showError("Cannot reach the server.");
        return;
      }
      var elapsed = Math.round(performance.now() - started);

      var data = null;
      try { data = await response.json(); } catch (e) { /* no JSON */ }
      captureBtn.disabled = false;

      if (!response.ok) {
        summary.textContent = "The server refused the frame (" + response.status + ").";
        rawBox.textContent = JSON.stringify(data, null, 2);
        showError(messageFor({ data: data }));
        return;
      }

      summary.textContent =
        "Faces found: " + data.faces_found +
        ". Unrecognized: " + data.unrecognized_faces +
        ". Took " + elapsed + " ms.";
      rawBox.textContent = JSON.stringify(data, null, 2);
    }, "image/jpeg", 0.9);
  });

  logoutBtn.addEventListener("click", async function () {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    await apiRequest("/auth/logout", { method: "POST" });
    window.location.replace("/login");
  });

  apiRequest("/auth/me").then(function (me) {
    if (!me.ok || !me.data || me.data.role !== "teacher") {
      window.location.replace("/login");
      return;
    }
    document.getElementById("teacher-name").textContent = me.data.full_name;
  });
})();