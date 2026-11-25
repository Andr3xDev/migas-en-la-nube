const pesoFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatPeso(amount) {
  return pesoFormatter.format(amount);
}

export function formatAvailability(availability) {
  if (availability.status === "in stock") return "Disponible";
  return `Por encargo (listo en ${availability.readyMinutes} min)`;
}

export function availabilityBadgeClass(inStock) {
  return `badge ${inStock ? "badge-in-stock" : "badge-made-to-order"}`;
}

export const PLACEHOLDER_IMAGE = "/img/placeholder.svg";

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
