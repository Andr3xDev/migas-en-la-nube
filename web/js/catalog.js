import { apiFetch } from "./api.js";
import {
  createProductImage,
  formatAvailability,
  formatPeso,
  showMessage,
} from "./format.js";

function createCard(product) {
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
  return card;
}

const container = document.getElementById("catalog");

try {
  const products = await apiFetch("/api/products");
  if (products.length === 0) {
    showMessage(container, "Aún no hay productos disponibles.");
  } else {
    container.replaceChildren(...products.map(createCard));
  }
} catch {
  showMessage(container, "No pudimos cargar el catálogo. Intenta de nuevo más tarde.");
}
