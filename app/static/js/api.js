// One place for talking to the backend. Never throws: always returns a result object.

// Turns one FastAPI validation error into a readable phrase, e.g. "academic year: use a format like 2026-2027".
function describeValidationError(item) {
  var loc = Array.isArray(item.loc) ? item.loc : [];
  var field = loc.length ? String(loc[loc.length - 1]) : "";
  var msg = String(item.msg || "is invalid").replace(/^Value error, /, "");

  if (field === "academic_year" && msg.indexOf("pattern") !== -1) {
    msg = "use a format like 2026-2027";
  } else if (msg.indexOf("pattern") !== -1) {
    msg = "has an invalid format";
  }

  if (!field || field === "body") return msg;
  return field.replace(/_/g, " ") + ": " + msg;
}

async function apiRequest(path, options) {
  options = options || {};
  var headers = { Accept: "application/json" };
  var init = {
    method: options.method || "GET",
    headers: headers,
    credentials: "same-origin",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }

  var response;
  try {
    response = await fetch(path, init);
  } catch (e) {
    return { ok: false, status: 0, data: null, networkError: true };
  }

  var data = null;
  try {
    data = await response.json();
  } catch (e) {
    /* response had no JSON body */
  }

  // Validation errors arrive as a list. Turn them into one sentence the screens can show.
  if (!response.ok && data && Array.isArray(data.detail)) {
    data.detail = data.detail.map(describeValidationError).join(". ");
  }

  return { ok: response.ok, status: response.status, data: data, networkError: false };
}