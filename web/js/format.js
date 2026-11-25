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

export function showMessage(container, text) {
  container.replaceChildren();
  const p = document.createElement("p");
  p.className = "message";
  p.textContent = text;
  container.append(p);
}
