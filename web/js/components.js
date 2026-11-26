import { isAdmin } from "./auth.js";
import {
  addProductVariant,
  CART_CHANGED_EVENT,
  getProductQuantity,
  MAX_LINE_QUANTITY_MESSAGE,
} from "./cart.js";
import { createFavoriteButton } from "./favorites.js";
import {
  availabilityBadgeClass,
  createProductImage,
  formatPeso,
  formatVariantAvailability,
  isInStock,
} from "./format.js";
import { createIcon, createIconButton, createIconLink } from "./icons.js";

export function createProductCard(product, { favorites, headingLevel = 2, onAdd } = {}) {
  const link = document.createElement("a");
  link.className = "product-link";
  link.href = `/product.html?id=${encodeURIComponent(product.id)}`;

  const name = document.createElement(`h${headingLevel}`);
  name.textContent = product.name;

  const lowest = product.variants.reduce((best, variant) =>
    variant.price < best.price ? variant : best,
  );
  // Badge describes the variant "Agregar" adds, so it never hides that variant's real stock.
  const availability = document.createElement("p");
  availability.className = availabilityBadgeClass(isInStock(lowest.availability));
  availability.textContent = formatVariantAvailability(lowest);

  link.append(createProductImage(product), name, availability);

  const price = document.createElement("p");
  price.className = "card-price";
  price.textContent =
    product.variants.length > 1 ? `Desde ${formatPeso(lowest.price)}` : formatPeso(lowest.price);

  const feedback = document.createElement("span");
  feedback.setAttribute("role", "status");
  const addButton = createIconButton({
    icon: "plus",
    label: `Agregar ${product.name} (${lowest.name}) al carrito`,
    variant: "primary",
    onClick: () => {
      const added = addProductVariant(product, lowest);
      if (onAdd) onAdd(product, added);
      else feedback.textContent = added ? `Agregado: ${lowest.name}` : MAX_LINE_QUANTITY_MESSAGE;
    },
  });

  const inCart = document.createElement("p");
  inCart.className = "in-cart";
  const refreshInCart = () => {
    const quantity = getProductQuantity(product.id);
    inCart.hidden = quantity === 0;
    inCart.textContent = `${quantity} en tu carrito`;
  };
  refreshInCart();
  // Listeners of cards that left the page unregister themselves on the next cart change.
  const onCartChanged = () => {
    if (card.isConnected) refreshInCart();
    else window.removeEventListener(CART_CHANGED_EVENT, onCartChanged);
  };
  window.addEventListener(CART_CHANGED_EVENT, onCartChanged);

  const actions = document.createElement("div");
  actions.className = "card-actions";
  if (favorites) actions.append(createFavoriteButton(product, favorites));
  if (!isAdmin()) actions.append(addButton);

  const footer = document.createElement("div");
  footer.className = "product-footer";
  footer.append(price, actions, feedback, inCart);

  const card = document.createElement("div");
  card.className = "product-card product-item";
  card.append(link, footer);
  return card;
}

// rows and total are [label, value] pairs.
export function createSummaryPanel({ title, rows, total, note }) {
  const panel = document.createElement("section");
  panel.className = "summary-panel";

  const heading = document.createElement("h2");
  heading.textContent = title;

  const list = document.createElement("dl");
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    list.append(term, detail);
  }
  const [totalLabel, totalValue] = total;
  const totalTerm = document.createElement("dt");
  totalTerm.textContent = totalLabel;
  const totalDetail = document.createElement("dd");
  totalDetail.textContent = totalValue;
  totalTerm.className = totalDetail.className = "summary-total";
  list.append(totalTerm, totalDetail);

  panel.append(heading, list);
  if (note) {
    const noteElement = document.createElement("p");
    noteElement.className = "summary-note";
    noteElement.append(createIcon("clock"), note);
    panel.append(noteElement);
  }
  return panel;
}

export function createEmptyState({ icon, title, text, action }) {
  const block = document.createElement("div");
  block.className = "empty-state";

  const heading = document.createElement("h2");
  heading.textContent = title;
  const description = document.createElement("p");
  description.textContent = text;

  block.append(createIcon(icon), heading, description);
  if (action) block.append(createIconLink(action));
  return block;
}

export function createLoadingState(text = "Cargando…", { announce = true } = {}) {
  const block = document.createElement("div");
  block.className = "loading-state";
  if (announce) {
    block.setAttribute("role", "status");
    block.setAttribute("aria-live", "polite");
  }
  const spinner = document.createElement("span");
  spinner.className = "spinner";
  spinner.setAttribute("aria-hidden", "true");
  block.append(spinner, text);
  return block;
}

export function createSkeletonCards(count) {
  return Array.from({ length: count }, () => {
    const card = document.createElement("div");
    card.className = "product-card skeleton-card";
    card.setAttribute("aria-hidden", "true");
    for (const part of ["skeleton-image", "skeleton-line", "skeleton-line skeleton-short"]) {
      const block = document.createElement("div");
      block.className = `skeleton ${part}`;
      card.append(block);
    }
    return card;
  });
}

// Containers are live regions already: the spinner stays silent and aria-busy marks the wait; endLoading clears it.
export function showLoading(container, content = createLoadingState(undefined, { announce: false })) {
  container.setAttribute("aria-busy", "true");
  container.replaceChildren(...[content].flat());
}

export function endLoading(container) {
  container.removeAttribute("aria-busy");
}

// For text-only buttons: the label is replaced by plain text, so icons are lost.
// Returns a function that restores the button's label and enables it again.
export function setBusy(button, busyText) {
  const label = button.textContent;
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  button.textContent = busyText;
  return () => {
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.textContent = label;
  };
}

function isOutsideBox(event, element) {
  const box = element.getBoundingClientRect();
  return (
    event.clientX < box.left ||
    event.clientX > box.right ||
    event.clientY < box.top ||
    event.clientY > box.bottom
  );
}

// A backdrop press targets the dialog itself but lies outside its box; padding presses are inside.
// Requiring the press to start on the backdrop keeps a drag that ends there from closing it.
export function closeDialogOnBackdropClick(dialog) {
  let pressedBackdrop = false;
  dialog.addEventListener("pointerdown", (event) => {
    pressedBackdrop = event.target === dialog && isOutsideBox(event, dialog);
  });
  dialog.addEventListener("click", (event) => {
    if (pressedBackdrop && event.target === dialog && isOutsideBox(event, dialog)) {
      dialog.close();
    }
    pressedBackdrop = false;
  });
}
