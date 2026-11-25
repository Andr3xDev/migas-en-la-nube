import { apiFetch, ApiError } from "./api.js";
import { clearCart, getCart, getTotal } from "./cart.js";
import { formatPeso, showMessage } from "./format.js";

const LAST_ORDER_KEY = "pdc.lastOrder";
const SHOP_UTC_OFFSET = "-05:00";

const form = document.getElementById("checkout-form");
const summary = document.getElementById("summary");
const feedback = document.getElementById("feedback");
const submit = document.getElementById("submit");

// datetime-local gives "YYYY-MM-DDTHH:mm"; the shop runs on fixed UTC-5.
const toPickupIso = (localValue) => `${localValue}:00${SHOP_UTC_OFFSET}`;

function renderSummary() {
  if (getCart().length === 0) {
    showMessage(summary, "Tu carrito está vacío.");
    form.hidden = true;
    return;
  }
  const total = document.createElement("p");
  total.className = "cart-total";
  total.textContent = `Total: ${formatPeso(getTotal())}`;
  summary.replaceChildren(total);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const items = getCart().map(({ productId, variantName, quantity }) => ({
    productId,
    variantName,
    quantity,
  }));
  if (items.length === 0) return;

  const data = new FormData(form);
  submit.disabled = true;
  try {
    const order = await apiFetch("/api/orders", {
      method: "POST",
      body: {
        customerName: data.get("customerName").trim(),
        phone: data.get("phone").trim(),
        pickupTime: toPickupIso(data.get("pickupTime")),
        items,
      },
    });
    localStorage.setItem(LAST_ORDER_KEY, order.code);
    clearCart();
    window.location.assign("/confirmation.html");
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.message);
    submit.disabled = false;
  }
});

renderSummary();
