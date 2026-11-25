export const TOKEN_KEY = "pdc.token";

const LOGIN_REQUIRED_PREFIXES = ["/api/me/", "/api/admin/"];

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["X-Pdc-Token"] = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  const payload = await response.json().catch(() => null);
  if (response.status === 401 && token) {
    // Drop the stale token so a retry goes out as a guest.
    localStorage.removeItem(TOKEN_KEY);
    // Only login-required routes redirect; guest-capable ones (checkout) show the error instead.
    if (LOGIN_REQUIRED_PREFIXES.some((prefix) => path.startsWith(prefix))) {
      window.location.assign("/login.html");
      // Never settle so callers do not flash an error while the page navigates.
      return new Promise(() => {});
    }
  }
  if (!response.ok) {
    const detail = payload && payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((issue) => issue.msg).filter(Boolean).join(". ")
      : detail;
    throw new ApiError(
      response.status,
      typeof message === "string" && message ? message : "Ocurrió un error inesperado.",
    );
  }
  return payload;
}
