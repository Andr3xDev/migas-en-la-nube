import { apiFetch, ApiError } from "./api.js";
import { setBusy } from "./components.js";
import { isAdmin, setToken } from "./auth.js";
import { showMessage } from "./format.js";

const GENERIC_LOGIN_ERROR = "Correo o contraseña incorrectos.";

const form = document.getElementById("login-form");
const feedback = document.getElementById("feedback");
const submit = document.getElementById("submit");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const restore = setBusy(submit, "Ingresando…");
  try {
    const { accessToken } = await apiFetch("/api/auth/login", {
      method: "POST",
      body: { email: data.get("email").trim(), password: data.get("password") },
    });
    setToken(accessToken);
    window.location.assign(isAdmin() ? "/admin/" : "/");
  } catch (error) {
    restore();
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.status === 401 ? GENERIC_LOGIN_ERROR : error.message);
  }
});
