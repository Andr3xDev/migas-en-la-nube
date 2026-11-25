import { getCart, getTotal, removeItem, setQuantity } from "./cart.js";
import { formatPeso, showMessage } from "./format.js";

const container = document.getElementById("cart");

function createCell(content) {
  const cell = document.createElement("td");
  cell.append(content);
  return cell;
}

function createRow(item) {
  const row = document.createElement("tr");

  const quantity = document.createElement("input");
  quantity.type = "number";
  quantity.min = "1";
  quantity.value = String(item.quantity);
  quantity.setAttribute("aria-label", `Cantidad de ${item.name}`);
  quantity.addEventListener("change", () => {
    const value = quantity.valueAsNumber;
    if (Number.isInteger(value) && value >= 1) {
      setQuantity(item.productId, item.variantName, value);
    }
    render();
  });

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button";
  remove.textContent = "Quitar";
  remove.addEventListener("click", () => {
    removeItem(item.productId, item.variantName);
    render();
  });

  row.append(
    createCell(item.name),
    createCell(formatPeso(item.price)),
    createCell(quantity),
    createCell(formatPeso(item.price * item.quantity)),
    createCell(remove),
  );
  return row;
}

function render() {
  const items = getCart();
  if (items.length === 0) {
    showMessage(container, "Tu carrito está vacío.");
    return;
  }

  const head = document.createElement("tr");
  for (const label of ["Producto", "Precio", "Cantidad", "Subtotal", ""]) {
    const th = document.createElement("th");
    th.textContent = label;
    head.append(th);
  }
  const table = document.createElement("table");
  table.className = "cart-table";
  table.append(head, ...items.map(createRow));

  const total = document.createElement("p");
  total.className = "cart-total";
  total.textContent = `Total: ${formatPeso(getTotal())}`;

  const checkout = document.createElement("a");
  checkout.className = "button";
  checkout.href = "/checkout.html";
  checkout.textContent = "Continuar con el pedido";

  container.replaceChildren(table, total, checkout);
}

render();
