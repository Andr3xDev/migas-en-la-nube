import { apiFetch } from "./api.js";
import { LAST_ORDER_KEY } from "./cart.js";

const SHOP_UTC_OFFSET = "-05:00";

// datetime-local gives "YYYY-MM-DDTHH:mm"; the shop runs on fixed UTC-5.
const toPickupIso = (localValue) => `${localValue}:00${SHOP_UTC_OFFSET}`;

// Mirrors create_order in api/app/services/orders.py: the wait is the longest prep time among
// lines whose stock cannot cover the quantity. Lines of unknown products add nothing.
export function estimateWaitMinutes(lines, catalog) {
  let wait = 0;
  for (const line of lines) {
    const product = catalog.find((candidate) => candidate.id === line.productId);
    const variant = product?.variants.find((candidate) => candidate.name === line.variantName);
    if (variant && variant.stock < line.quantity) wait = Math.max(wait, product.prepMinutes);
  }
  return wait;
}

export async function placeOrder(formData, lines) {
  const order = await apiFetch("/api/orders", {
    method: "POST",
    body: {
      customerName: formData.get("customerName").trim(),
      phone: formData.get("phone").trim(),
      pickupTime: toPickupIso(formData.get("pickupTime")),
      items: lines.map(({ productId, variantName, quantity }) => ({
        productId,
        variantName,
        quantity,
      })),
    },
  });
  localStorage.setItem(LAST_ORDER_KEY, order.code);
  return order;
}
