import { apiFetch, getToken } from "./api.js";

// Anonymous users and failed loads both yield null: no toggles are shown.
export async function loadFavorites() {
  if (!getToken()) return null;
  try {
    return new Set(await apiFetch("/api/me/favorites"));
  } catch {
    return null;
  }
}

export function createFavoriteButton(productId, favorites) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button";
  const refresh = () => {
    const marked = favorites.has(productId);
    button.textContent = marked ? "Quitar de favoritos" : "Agregar a favoritos";
    button.setAttribute("aria-pressed", String(marked));
  };
  refresh();
  button.addEventListener("click", async () => {
    const marked = favorites.has(productId);
    button.disabled = true;
    try {
      await apiFetch(`/api/me/favorites/${encodeURIComponent(productId)}`, {
        method: marked ? "DELETE" : "PUT",
      });
      if (marked) favorites.delete(productId);
      else favorites.add(productId);
      refresh();
    } catch {
      button.textContent = "No se pudo actualizar. Intenta de nuevo.";
    } finally {
      button.disabled = false;
    }
  });
  return button;
}
