import { getToken } from "./api.js";
import { isAdmin, logout } from "./auth.js";
import { CART_CHANGED_EVENT, getItemCount } from "./cart.js";
import { createIcon } from "./icons.js";

const SHOPPING_PAGES = ["/cart.html", "/checkout.html", "/confirmation.html"];

// A page restored from the back/forward cache keeps the nav of the session it was left in.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) window.location.reload();
});

const cartCount = document.getElementById("cart-count");
function refreshCartCount() {
  if (!cartCount) return;
  const count = getItemCount();
  cartCount.hidden = count === 0;
  cartCount.textContent = String(count);
  // A span's aria-label is not announced, so name the parent link instead.
  cartCount.parentElement.setAttribute(
    "aria-label",
    count === 0 ? "Carrito" : `Carrito, ${count} productos`,
  );
}

function renderNav() {
  const signedIn = Boolean(getToken());
  for (const link of document.querySelectorAll("[data-guest]")) link.hidden = signedIn;
  for (const link of document.querySelectorAll("[data-user]")) link.hidden = !signedIn;
  for (const link of document.querySelectorAll('header nav a[href="/cart.html"]')) {
    link.hidden = isAdmin();
  }

  // Admin pages already link to /admin/ in their own nav.
  if (isAdmin() && !window.location.pathname.startsWith("/admin/")) {
    const adminLink = document.createElement("a");
    adminLink.href = "/admin/";
    adminLink.dataset.icon = "shield-check";
    adminLink.textContent = "Administrar";
    document.querySelector("header nav").prepend(adminLink);
  }

  for (const link of document.querySelectorAll("header nav [data-icon]")) {
    link.prepend(createIcon(link.dataset.icon));
  }

  refreshCartCount();
  window.addEventListener(CART_CHANGED_EVENT, refreshCartCount);

  document.getElementById("logout").addEventListener("click", (event) => {
    event.preventDefault();
    logout();
    window.location.assign("/");
  });
}

if (isAdmin() && SHOPPING_PAGES.includes(window.location.pathname)) {
  window.location.replace("/admin/");
} else {
  renderNav();
}
