// Builds a table from rows of data. Cell values are set with textContent only.
// columns: [{ key: "name", label: "Name" }, ...]
// rows: array of plain objects.
// emptyText: shown when there are no rows.
function renderTable(container, columns, rows, emptyText) {
  container.textContent = "";

  if (!rows.length) {
    var empty = document.createElement("p");
    empty.className = "muted";
    empty.style.padding = "var(--space-4)";
    empty.textContent = emptyText || "No records yet.";
    container.appendChild(empty);
    return;
  }

  var table = document.createElement("table");
  var thead = document.createElement("thead");
  var headRow = document.createElement("tr");
  columns.forEach(function (col) {
    var th = document.createElement("th");
    th.scope = "col";
    th.textContent = col.label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  var tbody = document.createElement("tbody");
  rows.forEach(function (row) {
    var tr = document.createElement("tr");
    columns.forEach(function (col) {
      var td = document.createElement("td");
      var value = row[col.key];
      td.textContent = value === null || value === undefined ? "" : String(value);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  container.appendChild(table);
}