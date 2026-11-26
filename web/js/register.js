import { apiFetch, ApiError } from "./api.js";
import { setBusy } from "./components.js";
import { showMessage } from "./format.js";

const form = document.getElementById("register-form");
const feedback = document.getElementById("feedback");
const submit = document.getElementById("submit");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const restore = setBusy(submit, "Creando…");
  try {
    await apiFetch("/api/auth/register", {
      method: "POST",
      body: { email: data.get("email").trim(), password: data.get("password") },
    });
    window.location.assign("/login.html");
  } catch (error) {
    restore();
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.message);
  }
});
