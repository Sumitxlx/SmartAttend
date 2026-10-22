// Builds a table. Every value goes in with textContent, never innerHTML.
// columns: [{ key, label }]   rows: array of plain objects
// emptyText: shown when there are no rows
// actions (optional): [{ label, onClick(row) }], rendered as buttons in an Actions column
function renderTable(container, columns, rows, emptyText, actions) {
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
  if (actions && actions.length) {
    var actionTh = document.createElement("th");
    actionTh.scope = "col";
    actionTh.textContent = "Actions";
    headRow.appendChild(actionTh);
  }
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
    if (actions && actions.length) {
      var actionTd = document.createElement("td");
      var box = document.createElement("div");
      box.className = "row-actions";
      actions.forEach(function (action) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-secondary btn-small";
        btn.textContent = action.label;
        btn.addEventListener("click", function () {
          action.onClick(row);
        });
        box.appendChild(btn);
      });
      actionTd.appendChild(box);
      tr.appendChild(actionTd);
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}