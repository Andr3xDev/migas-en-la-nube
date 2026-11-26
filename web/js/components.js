import { isAdmin } from "./auth.js";
import { addProductVariant } from "./cart.js";
import { createFavoriteButton } from "./favorites.js";
import {
  availabilityBadgeClass,
  createProductImage,
  formatAvailability,
  formatPeso,
  isInStock,
} from "./format.js";
import { createIcon, createIconButton, createIconLink } from "./icons.js";

export function createProductCard(product, { favorites, headingLevel = 2, onAdd } = {}) {
  const link = document.createElement("a");
  link.className = "product-link";
  link.href = `/product.html?id=${encodeURIComponent(product.id)}`;

  const name = document.createElement(`h${headingLevel}`);
  name.textContent = product.name;

  const availability = document.createElement("p");
  availability.className = availabilityBadgeClass(
    product.variants.every((variant) => isInStock(variant.availability)),
  );
  availability.textContent = product.variants
    .map((variant) => formatAvailability(variant.availability))
    .filter((text, index, all) => all.indexOf(text) === index)
    .join(" / ");

  link.append(createProductImage(product), name, availability);

  const lowest = product.variants.reduce((best, variant) =>
    variant.price < best.price ? variant : best,
  );
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
      addProductVariant(product, lowest);
      if (onAdd) onAdd(product);
      else feedback.textContent = `Agregado: ${lowest.name}`;
    },
  });

  const actions = document.createElement("div");
  actions.className = "card-actions";
  if (favorites) actions.append(createFavoriteButton(product, favorites));
  if (!isAdmin()) actions.append(addButton);

  const footer = document.createElement("div");
  footer.className = "product-footer";
  footer.append(price, actions, feedback);

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
