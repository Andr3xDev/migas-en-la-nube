import { apiFetch, getToken } from "./api.js";
import { isAdmin } from "./auth.js";
import { addProductVariant } from "./cart.js";
import { findVariant } from "./checkout.js";
import { createProductCard, endLoading, showLoading } from "./components.js";
import { createStatusChip, formatPeso, showMessage } from "./format.js";
import { createIconButton } from "./icons.js";

const ORDERS_PAGE_SIZE = 10;

function renderProductCards(container, products, favorites, emptyText) {
  if (products.length === 0) return showMessage(container, emptyText);
  container.replaceChildren(...products.map((product) => createProductCard(product, { favorites, headingLevel: 3 })));
}

// Past lines whose product or variant left the catalog are skipped; price is always the current one.
function orderAgain(order, catalog, feedback) {
  let added = 0;
  for (const line of order.items) {
    const { product, variant } = findVariant(catalog, line.productId, line.variantName);
    if (!variant) continue;
    addProductVariant(product, variant, line.quantity);
    added += 1;
  }
  feedback.textContent =
    added === 0
      ? "Ningún producto de este pedido está disponible ahora."
      : added < order.items.length
        ? "Agregamos al carrito los productos que siguen disponibles."
        : "Agregamos el pedido al carrito.";
}

function createOrderSummary(order, catalog) {
  const units = order.items.reduce((sum, line) => sum + line.quantity, 0);
  const pickup = new Date(order.pickupTime).toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const code = document.createElement("h3");
  code.textContent = order.code;
  const details = document.createElement("p");
  details.className = "order-meta";
  details.textContent = `Recogida: ${pickup} · ${units} ${units === 1 ? "producto" : "productos"}`;
  const total = document.createElement("p");
  total.className = "card-price";
  total.textContent = formatPeso(order.total);

  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");
  const again = createIconButton({
    icon: "shopping-cart",
    label: "Pedir de nuevo",
    text: "Pedir de nuevo",
    onClick: () => orderAgain(order, catalog, feedback),
  });

  const summary = document.createElement("article");
  summary.className = "order-summary";
  summary.append(code, createStatusChip(order.status), details, total);
  if (!isAdmin()) summary.append(again, feedback);
  return summary;
}

function renderOrders(container, orders, catalog) {
  let shown = 0;
  const moreButton = document.createElement("button");
  moreButton.type = "button";
  moreButton.className = "button button-secondary load-more";
  moreButton.textContent = "Mostrar más";

  const showNextPage = () => {
    const page = orders
      .slice(shown, shown + ORDERS_PAGE_SIZE)
      .map((order) => createOrderSummary(order, catalog));
    moreButton.before(...page);
    shown += page.length;
    moreButton.hidden = shown >= orders.length;
    return page;
  };

  moreButton.addEventListener("click", () => {
    // The button may hide itself, so focus moves to the first new order.
    const [firstNew] = showNextPage();
    firstNew.tabIndex = -1;
    firstNew.focus();
  });
  container.replaceChildren(moreButton);
  showNextPage();
}

async function renderSection(container, load) {
  showLoading(container);
  try {
    await load();
  } catch {
    showMessage(container, "No pudimos cargar esta sección. Intenta de nuevo más tarde.");
  } finally {
    endLoading(container);
  }
}

async function main() {
  if (!getToken()) {
    window.location.assign("/login.html");
    return;
  }

  const ordersContainer = document.getElementById("orders");
  const favoritesContainer = document.getElementById("favorites");
  const topContainer = document.getElementById("top-products");
  // One shared set keeps every favorite toggle on the page consistent.
  let favoritesRequest = null;
  const getFavorites = () =>
    (favoritesRequest ??= apiFetch("/api/me/favorites").then((ids) => new Set(ids)));

  await Promise.all([
    renderSection(ordersContainer, async () => {
      const [orders, catalog] = await Promise.all([
        apiFetch("/api/me/orders"),
        apiFetch("/api/products"),
      ]);
      if (orders.length === 0) return showMessage(ordersContainer, "Aún no has hecho pedidos.");
      renderOrders(ordersContainer, orders, catalog);
    }),
    renderSection(favoritesContainer, async () => {
      const [favorites, catalog] = await Promise.all([getFavorites(), apiFetch("/api/products")]);
      renderProductCards(
        favoritesContainer,
        catalog.filter((product) => favorites.has(product.id)),
        favorites,
        "Aún no tienes favoritos.",
      );
    }),
    renderSection(topContainer, async () => {
      const [products, favorites] = await Promise.all([
        apiFetch("/api/me/top-products"),
        getFavorites(),
      ]);
      renderProductCards(
        topContainer,
        products,
        favorites,
        "Haz un pedido para ver tus productos más pedidos.",
      );
    }),
  ]);
}

await main();
