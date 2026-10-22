// Shared admin shell: checks the session, highlights the current page, and wires up sign-out.
// Each admin page calls adminPageInit("dashboard") (or the matching page name) once.
var ADMIN_NAV = [
  { key: "dashboard", label: "Overview", href: "/admin" },
  { key: "departments", label: "Departments", href: "/manage/departments" },
  { key: "classes", label: "Classes", href: "/manage/classes" },
  { key: "subjects", label: "Subjects", href: "/manage/subjects" },
  { key: "teachers", label: "Teachers", href: "/manage/teachers" },
  { key: "students", label: "Students", href: "/manage/students" },
  { key: "assignments", label: "Assignments", href: "/manage/assignments" },
];

function buildAdminNav(activeKey) {
  var nav = document.getElementById("admin-nav");
  if (!nav) return;
  var list = document.createElement("ul");
  ADMIN_NAV.forEach(function (item) {
    var li = document.createElement("li");
    var link = document.createElement("a");
    link.href = item.href;
    link.textContent = item.label;
    if (item.key === activeKey) link.setAttribute("aria-current", "page");
    li.appendChild(link);
    list.appendChild(li);
  });
  nav.textContent = "";
  nav.appendChild(list);
}

// Returns the signed-in admin, or sends the browser to /login and returns null.
async function requireAdmin() {
  var result = await apiRequest("/auth/me");
  if (!result.ok || !result.data || result.data.role !== "admin") {
    window.location.replace("/login");
    return null;
  }
  return result.data;
}

async function adminPageInit(activeKey) {
  buildAdminNav(activeKey);

  var logout = document.getElementById("logout-btn");
  if (logout) {
    logout.addEventListener("click", async function () {
      await apiRequest("/auth/logout", { method: "POST" });
      window.location.replace("/login");
    });
  }

  var admin = await requireAdmin();
  if (admin) {
    var who = document.getElementById("admin-name");
    if (who) who.textContent = admin.full_name;
  }
  return admin;
}