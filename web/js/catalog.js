import { apiFetch } from "./api.js";
import { createFavoriteButton, loadFavorites } from "./favorites.js";
import {
  availabilityBadgeClass,
  createProductImage,
  formatAvailability,
  formatPeso,
  showMessage,
} from "./format.js";

function createCard(product, favorites) {
  const link = document.createElement("a");
  link.className = "product-link";
  link.href = `/product.html?id=${encodeURIComponent(product.id)}`;

  const name = document.createElement("h2");
  name.textContent = product.name;

  const availability = document.createElement("p");
  availability.className = availabilityBadgeClass(
    product.variants.every((variant) => variant.availability.status === "in stock"),
  );
  availability.textContent = product.variants
    .map((variant) => formatAvailability(variant.availability))
    .filter((text, index, all) => all.indexOf(text) === index)
    .join(" / ");

  const price = document.createElement("p");
  price.className = "card-price";
  const lowest = Math.min(...product.variants.map((variant) => variant.price));
  price.textContent = `Desde ${formatPeso(lowest)}`;

  link.append(createProductImage(product), name, availability);

  const footer = document.createElement("div");
  footer.className = "product-footer";
  footer.append(price);
  if (favorites) footer.append(createFavoriteButton(product.id, favorites));

  const item = document.createElement("div");
  item.className = "product-card product-item";
  item.append(link, footer);
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
