export const TOKEN_KEY = "pdc.token";

const LOGIN_REQUIRED_PREFIXES = ["/api/me/", "/api/admin/"];

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export async function apiFetch(path, { method = "GET", body, redirectOnUnauthorized = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["X-Pdc-Token"] = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  const payload = await response.json().catch(() => null);
  if (response.status === 401 && token) {
    // Drop the stale token so a retry goes out as a guest.
    localStorage.removeItem(TOKEN_KEY);
    // Only login-required routes redirect; guest-capable ones (checkout) show the error instead.
    // Optional /api/me calls on public pages opt out so an expired token just turns the page into guest mode.
    if (redirectOnUnauthorized && LOGIN_REQUIRED_PREFIXES.some((prefix) => path.startsWith(prefix))) {
      window.location.assign("/login.html");
      // Never settle so callers do not flash an error while the page navigates.
      return new Promise(() => {});
    }
  }
  if (!response.ok) {
    throw new ApiError(response.status, toSpanishMessage(response.status, payload && payload.detail));
  }
  return payload;
}

// The API answers in English and sometimes with a bare id or email as detail; never show those.
const KNOWN_MESSAGES = {
  "Invalid credentials": "Correo o contraseña incorrectos.",
  "Email already registered": "Ese correo ya está registrado.",
  "Too many concurrent updates, try again": "Hubo demasiados cambios a la vez. Inténtalo de nuevo.",
  "Forbidden": "No tienes permiso para esta acción.",
  "Admins cannot place orders": "Los administradores no pueden hacer pedidos.",
  "pickupTime must include a timezone offset": "La hora de recogida no es válida.",
  "Pickup must be between 06:00 and 20:00": "La recogida debe ser entre las 6:00 y las 20:00.",
  "Pickup time is in the past": "La hora de recogida ya pasó.",
  "Pickup is before the preparation time": "La hora de recogida es antes de que el pedido esté listo.",
  "A product needs at least one variant": "Un producto necesita al menos una variante.",
  "Price and stock cannot be negative": "El precio y el stock no pueden ser negativos.",
  "Variant names must be unique": "Los nombres de las variantes deben ser únicos.",
  "prepMinutes cannot be negative": "El tiempo de preparación no puede ser negativo.",
  "imageUrl must point to the images container": "La imagen debe venir del contenedor de imágenes.",
};
const KNOWN_PREFIXES = [
  ["Unknown product", "Uno de los productos ya no está disponible."],
  ["Pickup cannot be more than", "La recogida no puede ser con más de 30 días de anticipación."],
  ["Cannot change status", "No se puede cambiar el estado del pedido."],
  ["Unknown status", "Estado de pedido no válido."],
  ["Unsupported image type", "Tipo de imagen no admitido."],
];
const STATUS_MESSAGES = {
  404: "No encontrado.",
  409: "Otro usuario modificó este dato; recarga e inténtalo de nuevo.",
  422: "Revisa los datos ingresados.",
};
const GENERIC_ERROR = "Ocurrió un error inesperado.";

function toSpanishMessage(status, detail) {
  if (typeof detail === "string") {
    if (Object.hasOwn(KNOWN_MESSAGES, detail)) return KNOWN_MESSAGES[detail];
    const prefixed = KNOWN_PREFIXES.find(([prefix]) => detail.startsWith(prefix));
    if (prefixed) return prefixed[1];
  }
  return STATUS_MESSAGES[status] ?? GENERIC_ERROR;
}
