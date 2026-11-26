// Classic synchronous script: it must run before first paint, which deferred ES modules cannot.
// Token key and role decoding duplicate api.js (TOKEN_KEY) and auth.js (getRole), the sources of truth.
(function () {
  var auth = "guest";
  var token = localStorage.getItem("pdc.token");
  if (token) {
    auth = "customer";
    try {
      var payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      if (JSON.parse(atob(payload)).role === "admin") auth = "admin";
    } catch (error) {
      // Undecodable tokens stay customers, as in auth.js isAdmin() and nav.js signedIn.
    }
  }
  document.documentElement.dataset.auth = auth;

  // Same outcomes as nav.js CUSTOMER_PAGES, account.js main() and admin/guard.js requireAdmin().
  var path = location.pathname;
  if (auth === "admin" && ["/cart.html", "/confirmation.html", "/account.html"].indexOf(path) !== -1) {
    location.replace("/admin/");
  } else if (auth === "guest" && (path === "/account.html" || path.indexOf("/admin/") === 0)) {
    location.replace("/login.html");
  }
})();
