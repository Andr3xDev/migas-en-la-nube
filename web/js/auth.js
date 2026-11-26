import { getToken, TOKEN_KEY } from "./api.js";

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

// The payload is decoded without verifying the signature: the result is for UI gating only,
// the API enforces roles on every request.
function getRole() {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(atob(payload));
    return typeof claims.role === "string" ? claims.role : null;
  } catch {
    return null;
  }
}

export const isAdmin = () => getRole() === "admin";
