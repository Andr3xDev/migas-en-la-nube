import { getToken } from "./api.js";
import { getRole, logout } from "./auth.js";

const signedIn = Boolean(getToken());
for (const link of document.querySelectorAll("[data-guest]")) link.hidden = signedIn;
for (const link of document.querySelectorAll("[data-user]")) link.hidden = !signedIn;

if (getRole() === "admin") {
  const adminLink = document.createElement("a");
  adminLink.href = "/admin/";
  adminLink.textContent = "Administrar";
  document.querySelector("header nav").prepend(adminLink);
}

document.getElementById("logout").addEventListener("click", (event) => {
  event.preventDefault();
  logout();
  window.location.assign("/");
});
