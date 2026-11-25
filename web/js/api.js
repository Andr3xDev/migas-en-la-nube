export const TOKEN_KEY = "pdc.token";

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
    // An expired or invalid token would also fail guest calls such as checkout; drop it.
    localStorage.removeItem(TOKEN_KEY);
    // Auth pages must keep their own error message instead of reloading.
    if (!path.startsWith("/api/auth/")) {
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
