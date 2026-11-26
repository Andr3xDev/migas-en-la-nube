import { apiFetch, getToken } from "./api.js";
import { createIconButton } from "./icons.js";

// Anonymous users and failed loads both yield null: no toggles are shown.
export async function loadFavorites() {
  if (!getToken()) return null;
  try {
    return new Set(await apiFetch("/api/me/favorites", { redirectOnUnauthorized: false }));
  } catch {
    return null;
  }
}

export function createFavoriteButton(product, favorites) {
  const productId = product.id;
  const label = document.createElement("span");
  const button = createIconButton({ icon: "heart", text: label });
  const refresh = () => {
    const marked = favorites.has(productId);
    const text = marked ? "Guardado" : "Guardar";
    label.textContent = text;
    button.classList.toggle("is-active", marked);
    // Accessible name starts with the visible text (WCAG 2.5.3).
    button.setAttribute("aria-label", `${text} ${product.name}`);
    button.setAttribute("aria-pressed", String(marked));
  };
  refresh();
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  button.addEventListener("click", async () => {
    const marked = favorites.has(productId);
    button.disabled = true;
    status.textContent = "";
    try {
      await apiFetch(`/api/me/favorites/${encodeURIComponent(productId)}`, {
        method: marked ? "DELETE" : "PUT",
      });
      if (marked) favorites.delete(productId);
      else favorites.add(productId);
      refresh();
    } catch {
      status.textContent = "No se pudo actualizar. Intenta de nuevo.";
    } finally {
      button.disabled = false;
    }
  });
  const wrapper = document.createElement("span");
  wrapper.className = "favorite-control";
  wrapper.append(button, status);
  return wrapper;
}
