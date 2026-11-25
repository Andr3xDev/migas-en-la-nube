import { LAST_ORDER_KEY } from "./cart.js";
import { showMessage } from "./format.js";

const container = document.getElementById("confirmation");
const code = localStorage.getItem(LAST_ORDER_KEY);

if (code) {
  const intro = document.createElement("p");
  intro.textContent = "Gracias por tu pedido. Tu código es:";
  const codeElement = document.createElement("p");
  codeElement.className = "cart-total";
  codeElement.textContent = code;
  container.replaceChildren(intro, codeElement);
} else {
  showMessage(container, "No hay un pedido reciente.");
}
