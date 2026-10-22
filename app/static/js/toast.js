// Short messages in the corner. Text is set with textContent, so it is never treated as HTML.
function showToast(message, kind) {
  var region = document.getElementById("toast-region");
  if (!region) return;

  var item = document.createElement("div");
  item.className = "toast toast-" + (kind === "error" ? "error" : "success");
  item.setAttribute("role", kind === "error" ? "alert" : "status");
  item.textContent = message;
  region.appendChild(item);

  setTimeout(function () {
    item.remove();
  }, 4000);
}