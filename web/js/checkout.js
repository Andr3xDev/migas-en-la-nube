import { apiFetch, ApiError, getToken } from "./api.js";
import { LAST_ORDER_KEY } from "./cart.js";

// Fixed UTC-5 (no DST).
const SHOP_UTC_OFFSET = "-05:00";

// datetime-local gives "YYYY-MM-DDTHH:mm".
const toPickupIso = (localValue) => `${localValue}:00${SHOP_UTC_OFFSET}`;

// The product is returned even when the variant is gone; both are undefined for unknown products.
export function findVariant(catalog, productId, variantName) {
  const product = catalog.find((candidate) => candidate.id === productId);
  const variant = product?.variants.find((candidate) => candidate.name === variantName);
  return { product, variant };
}

// Mirrors create_order in api/app/services/orders.py: the wait is the longest prep time among
// lines whose stock cannot cover the quantity. Lines of unknown products add nothing.
export function estimateWaitMinutes(lines, catalog) {
  let wait = 0;
  for (const line of lines) {
    const { product, variant } = findVariant(catalog, line.productId, line.variantName);
    if (variant && variant.stock < line.quantity) wait = Math.max(wait, product.prepMinutes);
  }
  return wait;
}

const SHOP_UTC_OFFSET_MS = -5 * 60 * 60 * 1000;
const PICKUP_HORIZON_MS = 30 * 24 * 60 * 60 * 1000;
const SESSION_EXPIRED_MESSAGE =
  "Tu sesión venció. Inicia sesión de nuevo o envía el pedido como invitado.";

// datetime-local wants shop wall-clock time; shifting by the offset makes toISOString print it.
const toShopLocalValue = (epochMs) =>
  new Date(epochMs + SHOP_UTC_OFFSET_MS).toISOString().slice(0, 16);

// Hints only; the server stays the source of truth for the pickup rules.
export function setPickupBounds(input) {
  const now = Date.now();
  input.min = toShopLocalValue(now);
  input.max = toShopLocalValue(now + PICKUP_HORIZON_MS);
}

export async function placeOrder(formData, lines) {
  const hadToken = Boolean(getToken());
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
  }).catch((error) => {
    if (error instanceof ApiError && error.status === 401 && hadToken) {
      throw new ApiError(401, SESSION_EXPIRED_MESSAGE);
    }
    throw error;
  });
  localStorage.setItem(LAST_ORDER_KEY, order.code);
  return order;
}
