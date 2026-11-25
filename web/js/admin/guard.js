import { getToken } from "../api.js";
import { getRole } from "../auth.js";
import { showMessage } from "../format.js";

// The role check is UI gating only: the API enforces the admin role on every request.
// Returns true when the panel may load its data; the caller must not request admin data otherwise.
export function requireAdmin(panel, feedback) {
  if (!getToken()) {
    window.location.assign("/login.html");
    return false;
  }
  if (getRole() !== "admin") {
    showMessage(feedback, "Acceso denegado: esta sección es solo para administradores.");
    return false;
  }
  panel.hidden = false;
  return true;
}
