import { apiFetch } from "./api.js";
import { createFavoriteButton, loadFavorites } from "./favorites.js";
import {
  createProductImage,
  formatAvailability,
  formatPeso,
  showMessage,
} from "./format.js";

function createCard(product, favorites) {
  const card = document.createElement("a");
  card.className = "product-card";
  card.href = `/product.html?id=${encodeURIComponent(product.id)}`;

  const name = document.createElement("h2");
  name.textContent = product.name;

  const availability = document.createElement("p");
  availability.textContent = product.variants
    .map((variant) => formatAvailability(variant.availability))
    .filter((text, index, all) => all.indexOf(text) === index)
    .join(" / ");

  const price = document.createElement("p");
  const lowest = Math.min(...product.variants.map((variant) => variant.price));
  price.textContent = `Desde ${formatPeso(lowest)}`;

  card.append(createProductImage(product), name, availability, price);
  if (!favorites) return card;

  const item = document.createElement("div");
  item.append(card, createFavoriteButton(product.id, favorites));
  return item;
}

const container = document.getElementById("catalog");

try {
  const products = await apiFetch("/api/products");
  if (products.length === 0) {
    showMessage(container, "Aún no hay productos disponibles.");
  } else {
    const favorites = await loadFavorites();
    container.replaceChildren(...products.map((product) => createCard(product, favorites)));
  }
} catch {
  showMessage(container, "No pudimos cargar el catálogo. Intenta de nuevo más tarde.");
}
