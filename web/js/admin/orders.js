import { apiFetch, ApiError } from "../api.js";
import { createStatusChip, formatPeso, showMessage, STATUS_LABELS } from "../format.js";
import { requireAdmin } from "./guard.js";

const SHOP_TIMEZONE = "America/Bogota";

const NEXT_STATUS = { received: "preparing", preparing: "ready", ready: "delivered" };
const CANCELLABLE = ["received", "preparing", "ready"];

const panel = document.getElementById("panel");
const guardMessage = document.getElementById("guard-message");
const dateInput = document.getElementById("date");
const container = document.getElementById("orders");
const feedback = document.getElementById("feedback");

let orders = [];

function createCell(content, className = "") {
  const cell = document.createElement("td");
  cell.className = className;
  cell.append(content);
  return cell;
}

function createButton(label, onClick, variant = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `button ${variant}`.trim();
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function formatPickup(pickupTime) {
  return new Date(pickupTime).toLocaleTimeString("es-CO", {
    timeZone: SHOP_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
  });
}

function describeItems(order) {
  return order.items
    .map((item) => `${item.quantity} x ${item.productName} (${item.variantName})`)
    .join(", ");
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

function render() {
  if (orders.length === 0) {
    showMessage(container, "No hay pedidos para esta fecha.");
    return;
  }
  const table = document.createElement("table");
  table.className = "cart-table";
  const sorted = [...orders].sort((a, b) => new Date(a.pickupTime) - new Date(b.pickupTime));
  for (const order of sorted) {
    const row = document.createElement("tr");
    row.append(
      createCell(formatPickup(order.pickupTime), "cell-time"),
      createCell(`${order.customerName} (${order.phone})`),
      createCell(describeItems(order)),
      createCell(formatPeso(order.total)),
      createCell(createStatusChip(order.status)),
      createCell(createActions(order)),
    );
    table.append(row);
  }
  const scroller = document.createElement("div");
  scroller.className = "table-scroll";
  scroller.append(table);
  container.replaceChildren(scroller);
}

async function loadOrders() {
  feedback.replaceChildren();
  try {
    orders = await apiFetch(`/api/admin/orders?date=${encodeURIComponent(dateInput.value)}`);
    render();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(container, error.message);
  }
}

async function changeStatus(order, status) {
  feedback.replaceChildren();
  try {
    const updated = await apiFetch(
      `/api/admin/orders/${order.code}/status?date=${encodeURIComponent(dateInput.value)}`,
      { method: "PATCH", body: { status } },
    );
    orders = orders.map((item) => (item.code === updated.code ? updated : item));
    render();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.message);
  }
}

dateInput.addEventListener("change", () => {
  if (dateInput.value) loadOrders();
});

if (requireAdmin(panel, guardMessage)) {
  // en-CA formats as YYYY-MM-DD, the value format of a date input.
  dateInput.value = new Date().toLocaleDateString("en-CA", { timeZone: SHOP_TIMEZONE });
  loadOrders();
}
