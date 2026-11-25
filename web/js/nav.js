import { getToken } from "./api.js";
import { logout } from "./auth.js";

const signedIn = Boolean(getToken());
for (const link of document.querySelectorAll("[data-guest]")) link.hidden = signedIn;
for (const link of document.querySelectorAll("[data-user]")) link.hidden = !signedIn;

document.getElementById("logout").addEventListener("click", (event) => {
  event.preventDefault();
  logout();
  window.location.assign("/");
});
