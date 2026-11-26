import { isAdmin } from "./auth.js";
import { LAST_ORDER_KEY } from "./cart.js";
import { createEmptyState } from "./components.js";
import { createIcon, createIconButton, createIconLink } from "./icons.js";

const container = document.getElementById("confirmation");
const code = localStorage.getItem(LAST_ORDER_KEY);

function createCodeBlock(orderCode) {
  const intro = document.createElement("p");
  intro.textContent = "Gracias por tu pedido. Tu código es:";

  const codeElement = document.createElement("p");
  codeElement.className = "order-code";
  codeElement.textContent = orderCode;

  const feedback = document.createElement("p");
  feedback.setAttribute("role", "status");
  const copy = createIconButton({
    icon: "copy",
    label: "Copiar código",
    text: "Copiar",
    onClick: async () => {
      try {
        await navigator.clipboard.writeText(orderCode);
        feedback.textContent = "Código copiado.";
      } catch {
        feedback.textContent = "No se pudo copiar. Cópialo manualmente.";
      }
    },
  });

  const actions = document.createElement("div");
  actions.className = "confirmation-actions";
  actions.append(
    createIconLink({ icon: "arrow-left", text: "Volver al carro", href: "/cart.html", variant: "secondary" }),
    createIconLink({ icon: "utensils", text: "Ir al menú", href: "/" }),
  );

  const card = document.createElement("div");
  card.className = "confirmation-card";
  card.append(createIcon("check"), intro, codeElement, copy, feedback, actions);
  return card;
}

// Admins are redirected away by nav.js; skip rendering meanwhile.
if (!isAdmin()) {
  container.replaceChildren(
    code
      ? createCodeBlock(code)
      : createEmptyState({
          icon: "receipt",
          title: "No hay un pedido reciente",
          text: "Cuando hagas un pedido, aquí verás tu código.",
          action: { icon: "utensils", text: "Ir al menú", href: "/" },
        }),
  );
}
