import { apiFetch } from "./api.js";
import { addItem } from "./cart.js";
import {
  createProductImage,
  formatAvailability,
  formatPeso,
  showMessage,
} from "./format.js";

const container = document.getElementById("product");

function renderProduct(product) {
  const title = document.createElement("h1");
  title.textContent = product.name;

  const description = document.createElement("p");
  description.textContent = product.description;

  const select = document.createElement("select");
  select.setAttribute("aria-label", "Variante");
  product.variants.forEach((variant, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = variant.name;
    select.append(option);
  });

  const price = document.createElement("p");
  price.className = "cart-total";
  const availability = document.createElement("p");
  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");

  const selectedVariant = () => product.variants[Number(select.value)];
  const refresh = () => {
    price.textContent = formatPeso(selectedVariant().price);
    availability.textContent = formatAvailability(selectedVariant().availability);
    feedback.textContent = "";
  };
  select.addEventListener("change", refresh);
  refresh();

  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.className = "button";
  addButton.textContent = "Agregar al carrito";
  addButton.addEventListener("click", () => {
    const variant = selectedVariant();
    addItem({
      productId: product.id,
      variantName: variant.name,
      name: `${product.name} (${variant.name})`,
      price: variant.price,
    });
    feedback.textContent = "Agregado al carrito.";
  });

  const info = document.createElement("div");
  info.append(title, description, select, price, availability, addButton, feedback);

  const detail = document.createElement("div");
  detail.className = "product-detail";
  detail.append(createProductImage(product), info);
  container.replaceChildren(detail);
}

const productId = new URLSearchParams(location.search).get("id");

try {
  if (!productId) throw new Error("missing id");
  renderProduct(await apiFetch(`/api/products/${encodeURIComponent(productId)}`));
} catch {
  showMessage(container, "No pudimos cargar el producto. Intenta de nuevo más tarde.");
}
