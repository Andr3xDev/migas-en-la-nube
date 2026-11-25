import { apiFetch, getToken } from "./api.js";
import { addItem } from "./cart.js";
import { formatPeso, showMessage } from "./format.js";

function createProductLink(product) {
  const link = document.createElement("a");
  link.href = `/product.html?id=${encodeURIComponent(product.id)}`;
  link.textContent = product.name;
  return link;
}

function renderProductList(container, products, emptyText) {
  if (products.length === 0) return showMessage(container, emptyText);
  const list = document.createElement("ul");
  for (const product of products) {
    const entry = document.createElement("li");
    entry.append(createProductLink(product));
    list.append(entry);
  }
  container.replaceChildren(list);
}

// Past lines whose product or variant left the catalog are skipped; price is always the current one.
function orderAgain(order, catalog, feedback) {
  let added = 0;
  for (const line of order.items) {
    const product = catalog.find((candidate) => candidate.id === line.productId);
    const variant = product?.variants.find((candidate) => candidate.name === line.variantName);
    if (!variant) continue;
    addItem(
      {
        productId: product.id,
        variantName: variant.name,
        name: `${product.name} (${variant.name})`,
        price: variant.price,
      },
      line.quantity,
    );
    added += 1;
  }
  feedback.textContent =
    added === 0
      ? "Ningún producto de este pedido está disponible ahora."
      : added < order.items.length
        ? "Agregamos al carrito los productos que siguen disponibles."
        : "Agregamos el pedido al carrito.";
}

function createOrderCard(order, catalog) {
  const card = document.createElement("article");
  card.className = "product-card";

  const heading = document.createElement("h3");
  heading.textContent = `Pedido ${order.code}`;
  const details = document.createElement("p");
  details.textContent = `${order.status} - ${new Date(order.pickupTime).toLocaleString("es-CO")} - ${formatPeso(order.total)}`;

  const lines = document.createElement("ul");
  for (const line of order.items) {
    const entry = document.createElement("li");
    entry.textContent = `${line.quantity} x ${line.productName} (${line.variantName})`;
    lines.append(entry);
  }

  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button";
  button.textContent = "Pedir de nuevo";
  button.addEventListener("click", () => orderAgain(order, catalog, feedback));

  card.append(heading, details, lines, button, feedback);
  return card;
}

async function renderSection(container, load) {
  try {
    await load();
  } catch {
    showMessage(container, "No pudimos cargar esta sección. Intenta de nuevo más tarde.");
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

  await Promise.all([
    renderSection(ordersContainer, async () => {
      const [orders, catalog] = await Promise.all([
        apiFetch("/api/me/orders"),
        apiFetch("/api/products"),
      ]);
      if (orders.length === 0) return showMessage(ordersContainer, "Aún no has hecho pedidos.");
      ordersContainer.replaceChildren(...orders.map((order) => createOrderCard(order, catalog)));
    }),
    renderSection(favoritesContainer, async () => {
      const [ids, catalog] = await Promise.all([
        apiFetch("/api/me/favorites"),
        apiFetch("/api/products"),
      ]);
      renderProductList(
        favoritesContainer,
        catalog.filter((product) => ids.includes(product.id)),
        "Aún no tienes favoritos.",
      );
    }),
    renderSection(topContainer, async () => {
      renderProductList(
        topContainer,
        await apiFetch("/api/me/top-products"),
        "Haz un pedido para ver tus productos más pedidos.",
      );
    }),
  ]);
}

await main();
