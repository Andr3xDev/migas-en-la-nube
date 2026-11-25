import { apiFetch } from "./api.js";
import { addProductVariant } from "./cart.js";
import { createFavoriteButton, loadFavorites } from "./favorites.js";
import { createIconButton, createIconLink } from "./icons.js";
import {
  availabilityBadgeClass,
  createProductImage,
  formatAvailability,
  formatPeso,
  showMessage,
} from "./format.js";

const container = document.getElementById("product");

function renderProduct(product, favorites) {
  const title = document.createElement("h1");
  title.textContent = product.name;

  const description = document.createElement("p");
  description.className = "product-description";
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
  price.className = "price";
  const availability = document.createElement("p");
  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");

  const selectedVariant = () => product.variants[Number(select.value)];
  const refresh = () => {
    price.textContent = formatPeso(selectedVariant().price);
    availability.className = availabilityBadgeClass(selectedVariant().availability.status === "in stock");
    availability.textContent = formatAvailability(selectedVariant().availability);
    feedback.textContent = "";
  };
  select.addEventListener("change", refresh);
  refresh();

  const addButton = createIconButton({
    icon: "shopping-cart",
    label: "Agregar al carrito",
    text: "Agregar al carrito",
    variant: "primary",
    onClick: () => {
      addProductVariant(product, selectedVariant());
      feedback.textContent = "Agregado al carrito.";
    },
  });

  const actions = document.createElement("div");
  actions.className = "card-actions";
  actions.append(addButton);
  if (favorites) actions.append(createFavoriteButton(product.id, favorites));

  const info = document.createElement("div");
  info.className = "product-info";
  info.append(title, description, select, price, availability, actions, feedback);

  const detail = document.createElement("div");
  detail.className = "product-detail";
  detail.append(createProductImage(product), info);

  const back = createIconLink({ icon: "arrow-left", text: "Volver al menú", href: "/", variant: "secondary" });
  back.classList.add("back-link");
  container.replaceChildren(back, detail);
}

const productId = new URLSearchParams(location.search).get("id");

try {
  if (!productId) throw new Error("missing id");
  const product = await apiFetch(`/api/products/${encodeURIComponent(productId)}`);
  renderProduct(product, await loadFavorites());
} catch {
  showMessage(container, "No pudimos cargar el producto. Intenta de nuevo más tarde.");
}
