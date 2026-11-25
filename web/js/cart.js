const CART_KEY = "pdc.cart";
export const LAST_ORDER_KEY = "pdc.lastOrder";

const isValidLine = (item) =>
  item !== null &&
  typeof item === "object" &&
  typeof item.productId === "string" &&
  typeof item.variantName === "string" &&
  Number.isInteger(item.price) &&
  item.price >= 0 &&
  Number.isInteger(item.quantity) &&
  item.quantity > 0;

function load() {
  try {
    const items = JSON.parse(localStorage.getItem(CART_KEY));
    return Array.isArray(items) ? items.filter(isValidLine) : [];
  } catch {
    return [];
  }
}

export const CART_CHANGED_EVENT = "pdc:cart-changed";

function save(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(CART_CHANGED_EVENT));
}

const sameLine = (item, productId, variantName) =>
  item.productId === productId && item.variantName === variantName;

export function getCart() {
  return load();
}

export function addItem({ productId, variantName, name, price }, quantity = 1) {
  const items = load();
  const existing = items.find((item) => sameLine(item, productId, variantName));
  if (existing) {
    existing.quantity += quantity;
  } else {
    items.push({ productId, variantName, name, price, quantity });
  }
  save(items);
}

export function addProductVariant(product, variant, quantity = 1) {
  addItem(
    {
      productId: product.id,
      variantName: variant.name,
      name: `${product.name} (${variant.name})`,
      price: variant.price,
    },
    quantity,
  );
}

export function getItemCount() {
  return load().reduce((sum, item) => sum + item.quantity, 0);
}

export function setQuantity(productId, variantName, quantity) {
  if (!Number.isInteger(quantity)) return;
  if (quantity < 1) return removeItem(productId, variantName);
  const items = load();
  const existing = items.find((item) => sameLine(item, productId, variantName));
  if (existing) existing.quantity = quantity;
  save(items);
}

export function removeItem(productId, variantName) {
  save(load().filter((item) => !sameLine(item, productId, variantName)));
}

export const lineKey = (item) => `${item.productId}\u0000${item.variantName}`;

export function getTotal(items = load()) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

export function clearCart() {
  localStorage.removeItem(CART_KEY);
  window.dispatchEvent(new Event(CART_CHANGED_EVENT));
}
