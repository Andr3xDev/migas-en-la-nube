import { apiFetch } from "./api.js";
import { createProductCard, createSkeletonCards, endLoading, showLoading } from "./components.js";
import { loadFavorites } from "./favorites.js";
import { showMessage } from "./format.js";

const SKELETON_CARD_COUNT = 8;

const container = document.getElementById("catalog");

showLoading(container, createSkeletonCards(SKELETON_CARD_COUNT));
try {
  const products = await apiFetch("/api/products");
  if (products.length === 0) {
    showMessage(container, "Aún no hay productos disponibles.");
  } else {
    const favorites = await loadFavorites();
    container.replaceChildren(
      ...products.map((product) => createProductCard(product, { favorites })),
    );
  }
} catch {
  showMessage(container, "No pudimos cargar el catálogo. Intenta de nuevo más tarde.");
} finally {
  endLoading(container);
}
