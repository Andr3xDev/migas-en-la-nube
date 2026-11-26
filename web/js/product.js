import { apiFetch } from "./api.js";
import { isAdmin } from "./auth.js";
import {
  addProductVariant,
  CART_CHANGED_EVENT,
  getLineQuantity,
  MAX_LINE_QUANTITY_MESSAGE,
} from "./cart.js";
import { endLoading, showLoading } from "./components.js";
import { createFavoriteButton, loadFavorites } from "./favorites.js";
import { createIconButton, createIconLink } from "./icons.js";
import {
  availabilityBadgeClass,
  createProductImage,
  formatMinutes,
  formatPeso,
  formatVariantAvailability,
  isInStock,
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
  const inCart = document.createElement("p");
  inCart.className = "in-cart";
  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");

  const selectedVariant = () => product.variants[Number(select.value)];
  const refreshInCart = () => {
    const variant = selectedVariant();
    const quantity = getLineQuantity(product.id, variant.name);
    inCart.hidden = quantity === 0;
    inCart.textContent = `${quantity} en tu carrito`;
    if (quantity > 0 && quantity >= variant.stock) {
      inCart.append(
        ` · Con lo que llevas, el pedido es por encargo: listo en ${formatMinutes(product.prepMinutes)}`,
      );
    }
  };
  const refresh = () => {
    price.textContent = formatPeso(selectedVariant().price);
    availability.className = availabilityBadgeClass(isInStock(selectedVariant().availability));
    availability.textContent = formatVariantAvailability(selectedVariant());
    feedback.textContent = "";
    refreshInCart();
  };
  select.addEventListener("change", refresh);
  window.addEventListener(CART_CHANGED_EVENT, refreshInCart);
  refresh();

  const addButton = createIconButton({
    icon: "shopping-cart",
    label: "Agregar al carrito",
    text: "Agregar al carrito",
    variant: "primary",
    onClick: () => {
      const added = addProductVariant(product, selectedVariant());
      feedback.textContent = added ? "Agregado al carrito." : MAX_LINE_QUANTITY_MESSAGE;
    },
  });

  const actions = document.createElement("div");
  actions.className = "card-actions";
  if (!isAdmin()) actions.append(addButton);
  if (favorites) actions.append(createFavoriteButton(product, favorites));

  const info = document.createElement("div");
  info.className = "product-info";
  info.append(title, description, select, price, availability, inCart, actions, feedback);

  const detail = document.createElement("div");
  detail.className = "product-detail";
  detail.append(createProductImage(product), info);

  const back = createIconLink({ icon: "arrow-left", text: "Volver al menú", href: "/", variant: "secondary" });
  back.classList.add("back-link");
  container.replaceChildren(back, detail);
}

const productId = new URLSearchParams(location.search).get("id");

showLoading(container);
try {
  if (!productId) throw new Error("missing id");
  const product = await apiFetch(`/api/products/${encodeURIComponent(productId)}`);
  renderProduct(product, await loadFavorites());
} catch {
  showMessage(container, "No pudimos cargar el producto. Intenta de nuevo más tarde.");
} finally {
  endLoading(container);
}
