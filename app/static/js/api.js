// One place for talking to the backend. Never throws: always returns a result object.
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
  return { ok: response.ok, status: response.status, data: data, networkError: false };
}