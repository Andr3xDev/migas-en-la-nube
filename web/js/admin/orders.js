import { apiFetch, ApiError } from "../api.js";
import { createEmptyState, endLoading, showLoading } from "../components.js";
import { createStatusChip, formatPeso, showMessage, STATUS_LABELS } from "../format.js";
import { requireAdmin } from "./guard.js";
import { createButton, createCell, createTableHead, createTableScroller } from "./table.js";

const SHOP_TIMEZONE = "America/Bogota";
// Mirrors HISTORY_LIMIT in api/app/services/orders.py: a full page means older orders are hidden.
const HISTORY_LIMIT = 100;
const UPCOMING = "upcoming";
const HISTORY = "history";
const UPCOMING_COLUMNS = 6;

const NEXT_STATUS = { received: "preparing", preparing: "ready", ready: "delivered" };
const CANCELLABLE = ["received", "preparing", "ready"];
const UPCOMING_HEADINGS = ["Hora", "Cliente", "Productos", "Total", "Estado", "Acciones"];
const HISTORY_HEADINGS =["Código", "Entrega", "Cliente", "Estado", "Productos", "Total"];

const panel = document.getElementById("panel");
const guardMessage = document.getElementById("guard-message");
const dateInput = document.getElementById("date");
const clearDateButton = document.getElementById("clear-date");
const viewButtons = {
  [UPCOMING]: document.getElementById("view-upcoming"),
  [HISTORY]: document.getElementById("view-history"),
};
const container = document.getElementById("orders");
const feedback = document.getElementById("feedback");

let view = UPCOMING;
let orders = [];
let latestRequest = 0;

function formatPickup(pickupTime) {
  return new Date(pickupTime).toLocaleTimeString("es-CO", {
    timeZone: SHOP_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPickupDateTime(pickupTime) {
  return new Date(pickupTime).toLocaleString("es-CO", {
    timeZone: SHOP_TIMEZONE,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDay(pickupDate) {
  // Noon avoids a day shift when the browser timezone differs from the date's own.
  return new Date(`${pickupDate}T12:00:00`).toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function describeItems(order) {
  return order.items
    .map((item) => `${item.quantity} x ${item.productName} (${item.variantName})`)
    .join(", ");
}

function countUnits(order) {
  return order.items.reduce((sum, item) => sum + item.quantity, 0);
}

function createActions(order) {
  const actions = document.createElement("div");
  actions.className = "table-actions";
  const next = NEXT_STATUS[order.status];
  if (next) actions.append(createButton(`Pasar a ${STATUS_LABELS[next]}`, () => changeStatus(order, next)));
  if (CANCELLABLE.includes(order.status)) {
    actions.append(createButton("Cancelar", () => changeStatus(order, "cancelled"), "button-danger"));
  }
  return actions;
}

function createDayHeading(pickupDate) {
  const row = document.createElement("tr");
  row.className = "date-heading";
  const heading = document.createElement("th");
  heading.colSpan = UPCOMING_COLUMNS;
  heading.scope = "colgroup";
  heading.textContent = formatDay(pickupDate);
  row.append(heading);
  return row;
}

function createUpcomingRow(order) {
  const row = document.createElement("tr");
  row.append(
    createCell(formatPickup(order.pickupTime), "cell-time"),
    createCell(`${order.customerName} (${order.phone})`),
    createCell(describeItems(order)),
    createCell(formatPeso(order.total)),
    createCell(createStatusChip(order.status)),
    createCell(createActions(order)),
  );
  return row;
}

function createHistoryRow(order) {
  const row = document.createElement("tr");
  row.append(
    createCell(order.code, "cell-code"),
    createCell(formatPickupDateTime(order.pickupTime), "cell-time"),
    createCell(order.customerName),
    createCell(createStatusChip(order.status)),
    createCell(String(countUnits(order))),
    createCell(formatPeso(order.total)),
  );
  return row;
}

function createEmpty() {
  const text = {
    [UPCOMING]: "No hay pedidos próximos.",
    [HISTORY]: "Aún no hay pedidos anteriores.",
  };
  return createEmptyState({
    icon: "receipt",
    title: "Sin pedidos",
    text: dateInput.value ? "No hay pedidos para esta fecha." : text[view],
  });
}

function render() {
  if (orders.length === 0) {
    container.replaceChildren(createEmpty());
    return;
  }
  const isHistory = view === HISTORY && !dateInput.value;
  const table = document.createElement("table");
  table.className = "cart-table";
  table.append(createTableHead(isHistory ? HISTORY_HEADINGS : UPCOMING_HEADINGS));
  if (isHistory) {
    table.append(...orders.map(createHistoryRow));
  } else {
    let currentDay = null;
    for (const order of orders) {
      if (order.pickupDate !== currentDay) {
        currentDay = order.pickupDate;
        table.append(createDayHeading(currentDay));
      }
      table.append(createUpcomingRow(order));
    }
  }
  container.replaceChildren(createTableScroller(table, "Pedidos"));
  if (isHistory && orders.length >= HISTORY_LIMIT) {
    const note = document.createElement("p");
    note.className = "orders-note";
    note.textContent = `Se muestran los ${HISTORY_LIMIT} más recientes; puede haber pedidos más antiguos.`;
    container.append(note);
  }
}

function syncControls() {
  const filtered = Boolean(dateInput.value);
  for (const [name, button] of Object.entries(viewButtons)) {
    button.setAttribute("aria-pressed", String(!filtered && name === view));
  }
  clearDateButton.hidden = !filtered;
}

async function loadOrders() {
  feedback.replaceChildren();
  syncControls();
  const query = dateInput.value
    ? `date=${encodeURIComponent(dateInput.value)}`
    : `scope=${view}`;
  const requestId = ++latestRequest;
  showLoading(container);
  try {
    const loaded = await apiFetch(`/api/admin/orders?${query}`);
    if (requestId !== latestRequest) return;
    orders = loaded;
    render();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (requestId === latestRequest) showMessage(container, error.message);
  } finally {
    // A stale response must not clear the busy mark of the newer request.
    if (requestId === latestRequest) endLoading(container);
  }
}

async function changeStatus(order, status) {
  feedback.replaceChildren();
  try {
    const updated = await apiFetch(
      `/api/admin/orders/${encodeURIComponent(order.code)}/status?date=${encodeURIComponent(order.pickupDate)}`,
      { method: "PATCH", body: { status } },
    );
    orders = orders.map((item) => (item.code === updated.code ? updated : item));
    render();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.message);
  }
}

for (const [name, button] of Object.entries(viewButtons)) {
  button.addEventListener("click", () => {
    view = name;
    dateInput.value = "";
    loadOrders();
  });
}

dateInput.addEventListener("change", loadOrders);

clearDateButton.addEventListener("click", () => {
  dateInput.value = "";
  loadOrders();
});

if (requireAdmin(panel, guardMessage)) loadOrders();
