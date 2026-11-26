const pesoFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatPeso(amount) {
  return pesoFormatter.format(amount);
}

const IN_STOCK = "in stock";

export const isInStock = (availability) => availability.status === IN_STOCK;

function formatAvailability(availability) {
  if (isInStock(availability)) return "Disponible";
  return `Por encargo (listo en ${formatMinutes(availability.readyMinutes)})`;
}

export function formatVariantAvailability(variant) {
  const text = formatAvailability(variant.availability);
  return variant.stock > 0 ? `${text} · Quedan ${variant.stock}` : text;
}

const MINUTES_PER_HOUR = 60;

export function formatMinutes(minutes) {
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  const rest = minutes % MINUTES_PER_HOUR;
  if (hours === 0) return `${minutes} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

export function availabilityBadgeClass(inStock) {
  return `badge ${inStock ? "badge-in-stock" : "badge-made-to-order"}`;
}

const PLACEHOLDER_IMAGE = "/img/placeholder.svg";

export function createProductImage(product) {
  const img = document.createElement("img");
  img.src = product.imageUrl || PLACEHOLDER_IMAGE;
  img.alt = product.name;
  img.addEventListener(
    "error",
    () => {
      img.src = PLACEHOLDER_IMAGE;
    },
    { once: true },
  );
  return img;
}

export const STATUS_LABELS = {
  received: "Recibido",
  preparing: "En preparación",
  ready: "Listo",
  delivered: "Entregado",
  cancelled: "Cancelado",
};

export function createStatusChip(status) {
  const chip = document.createElement("span");
  chip.className = `chip chip-${status}`;
  chip.textContent = STATUS_LABELS[status] ?? status;
  return chip;
}

export function showMessage(container, text, kind = "error") {
  container.replaceChildren();
  const p = document.createElement("p");
  p.className = kind === "success" ? "message message-success" : "message";
  p.textContent = text;
  container.append(p);
}
