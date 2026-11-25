import { apiFetch, ApiError } from "./api.js";
import {
  CART_CHANGED_EVENT,
  getCart,
  getTotal,
  lineKey,
  removeItem,
  setQuantity,
} from "./cart.js";
import { estimateWaitMinutes, placeOrder } from "./checkout.js";
import { createEmptyState, createProductCard, createSummaryPanel } from "./components.js";
import { loadFavorites } from "./favorites.js";
import { createProductImage, formatMinutes, formatPeso, showMessage } from "./format.js";
import { createIcon, createIconButton } from "./icons.js";

const MAX_RECOMMENDATIONS = 3;

const itemsContainer = document.getElementById("cart-items");
const summaryContainer = document.getElementById("cart-summary");
const form = document.getElementById("order-form");
const submit = document.getElementById("submit");
const feedback = document.getElementById("feedback");
const cartHeading = document.getElementById("cart-heading");
const addStatus = document.getElementById("add-status");
const recommendations = document.getElementById("recommendations");
const recommendationList = document.getElementById("recommendation-list");

// Lines are selected unless listed here, so newly added lines start selected.
const unselected = new Set();
let catalog = [];
let catalogLoaded = false;
let favorites = null;
let submitting = false;

const findProduct = (item) => catalog.find((product) => product.id === item.productId);
const findVariant = (item) =>
  findProduct(item)?.variants.find((variant) => variant.name === item.variantName);
const selectedLines = () => getCart().filter((item) => !unselected.has(lineKey(item)));

function createQuantityControl(item) {
  const input = document.createElement("input");
  input.type = "number";
  input.min = "1";
  input.value = String(item.quantity);
  input.setAttribute("aria-label", `Cantidad de ${item.name}`);
  input.addEventListener("change", () => {
    const value = input.valueAsNumber;
    if (Number.isInteger(value) && value >= 1) setQuantity(item.productId, item.variantName, value);
    else renderItems();
  });

  const step = (icon, label, delta) => {
    const button = createIconButton({
      icon,
      label: `${label} ${item.name}`,
      onClick: () => setQuantity(item.productId, item.variantName, item.quantity + delta),
    });
    button.dataset.focusKey = `${lineKey(item)}${icon}`;
    return button;
  };
  const minus = step("minus", "Quitar uno de", -1);
  minus.disabled = item.quantity <= 1;

  const control = document.createElement("div");
  control.className = "quantity-control";
  control.append(minus, input, step("plus", "Agregar uno de", 1));
  return control;
}

function createLineCard(item) {
  const product = findProduct(item);
  const variant = findVariant(item);

  const selectBox = document.createElement("input");
  selectBox.type = "checkbox";
  selectBox.checked = !unselected.has(lineKey(item));
  selectBox.addEventListener("change", () => {
    if (selectBox.checked) unselected.delete(lineKey(item));
    else unselected.add(lineKey(item));
    renderSide();
  });
  const selectLabel = document.createElement("label");
  selectLabel.className = "select-line";
  selectLabel.append(selectBox, "Pedir este");

  const name = document.createElement("h2");
  name.textContent = product?.name ?? item.name;
  const variantLine = document.createElement("p");
  variantLine.className = "line-variant";
  variantLine.textContent = product ? item.variantName : "";
  variantLine.hidden = !product;

  const price = document.createElement("p");
  price.className = "line-price";
  price.textContent = `${formatPeso(item.price)} c/u · ${formatPeso(item.price * item.quantity)}`;

  const prep = document.createElement("p");
  prep.className = "line-prep";
  if (variant) {
    prep.append(
      createIcon("clock"),
      variant.stock < item.quantity
        ? `Por encargo: listo en ${formatMinutes(product.prepMinutes)}`
        : "Disponible",
    );
  } else prep.hidden = true;

  const remove = createIconButton({
    icon: "trash-2",
    label: `Quitar ${item.name} del carrito`,
    text: "Quitar",
    onClick: () => removeItem(item.productId, item.variantName),
  });

  const controls = document.createElement("div");
  controls.className = "line-controls";
  controls.append(createQuantityControl(item), remove);

  const body = document.createElement("div");
  body.className = "line-body";
  body.append(name, variantLine, price, prep, controls, selectLabel);

  const card = document.createElement("article");
  card.className = "cart-line";
  card.append(createProductImage(product ?? { name: item.name, imageUrl: null }), body);
  return card;
}

// Adding re-renders the recommendation card, so announce and park focus outside it.
function announceAdded(product) {
  addStatus.textContent = `Agregado: ${product.name}`;
  cartHeading.focus();
}

function renderRecommendations(items) {
  const inCart = new Set(items.map((item) => item.productId));
  const cartCategories = new Set(items.map((item) => findProduct(item)?.category));
  const candidates = catalog.filter(
    (product) =>
      !inCart.has(product.id) &&
      product.variants.some((variant) => variant.availability.status === "in stock"),
  );
  const picks = [
    ...candidates.filter((product) => cartCategories.has(product.category)),
    ...candidates.filter((product) => !cartCategories.has(product.category)),
  ].slice(0, MAX_RECOMMENDATIONS);
  recommendations.hidden = picks.length === 0;
  recommendationList.replaceChildren(
    ...picks.map((product) =>
      createProductCard(product, { favorites, headingLevel: 3, onAdd: announceAdded }),
    ),
  );
}

function renderItems() {
  const focusKey = document.activeElement?.dataset?.focusKey;
  const items = getCart();
  if (items.length === 0) {
    itemsContainer.replaceChildren(
      createEmptyState({
        icon: "shopping-basket",
        title: "Tu carrito está vacío",
        text: "Agrega panes, tortas y galletas del menú para empezar tu pedido.",
        action: { icon: "utensils", text: "Ver el menú", href: "/" },
      }),
    );
  } else {
    itemsContainer.replaceChildren(...items.map(createLineCard));
  }
  renderRecommendations(items);
  renderSide();
  if (focusKey) {
    for (const button of itemsContainer.querySelectorAll("[data-focus-key]")) {
      if (button.dataset.focusKey === focusKey && !button.disabled) button.focus();
    }
  }
}

function renderSide() {
  const lines = selectedLines();
  const units = lines.reduce((sum, item) => sum + item.quantity, 0);
  const wait = estimateWaitMinutes(lines, catalog);
  let ready = "-";
  if (lines.length > 0) {
    if (!catalogLoaded) ready = "No disponible";
    else ready = wait === 0 ? "De inmediato" : `Hasta ${formatMinutes(wait)}`;
  }

  summaryContainer.replaceChildren(
    createSummaryPanel({
      title: "Resumen del pedido",
      rows: [
        ["Productos", String(units)],
        ["Listo en", ready],
      ],
      total: ["Total", formatPeso(getTotal(lines))],
      note: lines.length > 0 ? "Es un máximo: tu pedido puede estar listo antes." : null,
    }),
  );
  form.hidden = getCart().length === 0;
  submit.disabled = submitting || lines.length === 0;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const lines = selectedLines();
  if (lines.length === 0) return;

  submitting = true;
  submit.disabled = true;
  try {
    await placeOrder(new FormData(form), lines);
    for (const line of lines) removeItem(line.productId, line.variantName);
    window.location.assign("/confirmation.html");
  } catch (error) {
    showMessage(
      feedback,
      error instanceof ApiError ? error.message : "No se pudo enviar el pedido. Intenta de nuevo.",
    );
    submitting = false;
    submit.disabled = false;
  }
});

window.addEventListener(CART_CHANGED_EVENT, renderItems);

renderItems();
try {
  [catalog, favorites] = await Promise.all([apiFetch("/api/products"), loadFavorites()]);
  catalogLoaded = true;
} catch {
  // Without the catalog the cart still works; images, prep times and recommendations are skipped.
}
renderItems();
