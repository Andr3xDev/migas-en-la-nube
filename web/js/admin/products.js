import { apiFetch, ApiError } from "../api.js";
import {
  closeDialogOnBackdropClick,
  createSummaryPanel,
  endLoading,
  setBusy,
  showLoading,
} from "../components.js";
import { createProductImage, formatPeso, showMessage } from "../format.js";
import { requireAdmin } from "./guard.js";
import { createButton, createCell } from "./table.js";

const UPLOAD_FAILED_MESSAGE = "No se pudo subir la imagen.";
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const STALE_PRODUCT_MESSAGE =
  "El producto cambió (por ejemplo, por un pedido). Recarga la página e inténtalo de nuevo.";

const panel = document.getElementById("panel");
const guardMessage = document.getElementById("guard-message");
const list = document.getElementById("product-list");
const summary = document.getElementById("summary");
const listFeedback = document.getElementById("list-feedback");
const dialog = document.getElementById("product-dialog");
const createButtonElement = document.getElementById("create-product");
const form = document.getElementById("product-form");
const formTitle = document.getElementById("form-title");
const variantsContainer = document.getElementById("variants");
const imageInput = document.getElementById("image");
const currentImage = document.getElementById("current-image");
const feedback = document.getElementById("feedback");
const submit = document.getElementById("submit");
const resetButton = document.getElementById("reset");

let products = [];
let editing = null;
let dialogTrigger = null;

function describeVariants(product) {
  return product.variants
    .map((variant) => `${variant.name}: ${formatPeso(variant.price)} (stock ${variant.stock})`)
    .join("; ");
}

function renderSummary() {
  const outOfStock = products.filter((product) =>
    product.variants.every((variant) => variant.stock <= 0),
  ).length;
  const perCategory = new Map();
  for (const product of products) {
    perCategory.set(product.category, (perCategory.get(product.category) ?? 0) + 1);
  }
  summary.replaceChildren(
    createSummaryPanel({
      title: "Resumen",
      rows: [["Agotados", String(outOfStock)], ...[...perCategory].map(([name, count]) => [name, String(count)])],
      total: ["Total de productos", String(products.length)],
    }),
  );
}

function renderList() {
  renderSummary();
  if (products.length === 0) {
    showMessage(list, "No hay productos.");
    return;
  }
  const table = document.createElement("table");
  table.className = "cart-table";
  for (const product of products) {
    const row = document.createElement("tr");
    const actions = document.createElement("div");
    actions.className = "table-actions";
    const editButton = createButton(
      "Editar",
      (event) => openDialog(event.currentTarget, product),
      "button-secondary",
    );
    editButton.dataset.editId = product.id;
    actions.append(editButton, createButton("Eliminar", () => removeProduct(product), "button-danger"));
    row.append(
      createCell(createProductImage(product)),
      createCell(product.name),
      createCell(product.category),
      createCell(describeVariants(product)),
      createCell(actions),
    );
    table.append(row);
  }
  const scroller = document.createElement("div");
  scroller.className = "table-scroll";
  scroller.append(table);
  list.replaceChildren(scroller);
}

function addVariantRow(variant = { name: "", price: "", stock: "" }) {
  const row = document.createElement("p");
  row.className = "variant-row";
  const fields = [
    ["name", "Nombre de la variante", "text", variant.name],
    ["price", "Precio final (COP)", "number", variant.price],
    ["stock", "Stock", "number", variant.stock],
  ];
  for (const [field, label, type, value] of fields) {
    const input = document.createElement("input");
    input.type = type;
    input.dataset.field = field;
    input.required = true;
    input.value = String(value);
    input.placeholder = label;
    input.setAttribute("aria-label", label);
    if (type === "number") {
      input.min = "0";
      input.step = "1";
    }
    row.append(input);
  }
  row.append(createButton("Quitar", () => row.remove(), "button-secondary"));
  variantsContainer.append(row);
}

function readVariants() {
  return [...variantsContainer.children].map((row) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`).value;
    return { name: value("name").trim(), price: Number(value("price")), stock: Number(value("stock")) };
  });
}

function renderCurrentImage() {
  currentImage.replaceChildren();
  if (editing && editing.imageUrl) currentImage.append(createProductImage(editing));
}

function resetForm() {
  editing = null;
  HTMLFormElement.prototype.reset.call(form);
  variantsContainer.replaceChildren();
  addVariantRow();
  formTitle.textContent = "Nuevo producto";
  renderCurrentImage();
}

function openDialog(trigger, product = null) {
  dialogTrigger = trigger;
  if (product) startEdit(product);
  else resetForm();
  feedback.replaceChildren();
  dialog.showModal();
}

function startEdit(product) {
  HTMLFormElement.prototype.reset.call(form);
  form.elements.name.value = product.name;
  form.elements.category.value = product.category;
  form.elements.description.value = product.description;
  form.elements.prepMinutes.value = String(product.prepMinutes);
  variantsContainer.replaceChildren();
  for (const variant of product.variants) addVariantRow(variant);
  startEditKeepingValues(product);
  renderCurrentImage();
}

function validateImage(file) {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return "La imagen debe ser JPEG, PNG o WebP.";
  if (file.size > MAX_IMAGE_BYTES) return "La imagen no puede superar 2 MB.";
  return null;
}

class UploadError extends Error {}

async function uploadImage(productId, file) {
  const { uploadUrl, imageUrl } = await apiFetch(`/api/admin/products/${encodeURIComponent(productId)}/image-upload-url`, {
    method: "POST",
    body: { contentType: file.type },
  });
  let response;
  try {
    response = await fetch(uploadUrl, {
      method: "PUT",
      headers: { "x-ms-blob-type": "BlockBlob", "Content-Type": file.type },
      body: file,
    });
  } catch {
    throw new UploadError(UPLOAD_FAILED_MESSAGE);
  }
  if (!response.ok) throw new UploadError(UPLOAD_FAILED_MESSAGE);
  return imageUrl;
}

async function loadProducts() {
  showLoading(summary);
  showLoading(list);
  try {
    products = await apiFetch("/api/products");
    renderList();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    summary.replaceChildren();
    showMessage(list, error.message);
  } finally {
    endLoading(summary);
    endLoading(list);
  }
}

async function removeProduct(product) {
  if (!window.confirm(`¿Eliminar "${product.name}"?`)) return;
  try {
    await apiFetch(`/api/admin/products/${encodeURIComponent(product.id)}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(listFeedback, error.message);
    return;
  }
  listFeedback.replaceChildren();
  products = products.filter((item) => item.id !== product.id);
  renderList();
}

function readPayload(imageUrl) {
  const data = new FormData(form);
  return {
    name: data.get("name").trim(),
    category: data.get("category").trim(),
    description: data.get("description").trim(),
    imageUrl,
    prepMinutes: Number(data.get("prepMinutes")),
    variants: readVariants(),
  };
}

function upsertLocal(saved) {
  const index = products.findIndex((item) => item.id === saved.id);
  if (index === -1) products.push(saved);
  else products[index] = saved;
  renderList();
}

async function updateProduct(id, body) {
  try {
    return await apiFetch(`/api/admin/products/${encodeURIComponent(id)}`, { method: "PUT", body });
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      throw new ApiError(409, STALE_PRODUCT_MESSAGE);
    }
    throw error;
  }
}

async function save(file) {
  const imageUrl = editing ? editing.imageUrl : null;
  let saved;
  if (!editing) {
    saved = await apiFetch("/api/admin/products", { method: "POST", body: readPayload(imageUrl) });
    upsertLocal(saved);
    if (!file) return saved;
    try {
      const newUrl = await uploadImage(saved.id, file);
      saved = await updateProduct(saved.id, { ...readPayload(newUrl), etag: saved.etag });
    } catch (error) {
      // The product exists already: keep the form in edit mode so the upload can be retried.
      startEditKeepingValues(saved);
      throw error;
    }
    return saved;
  }
  const newUrl = file ? await uploadImage(editing.id, file) : imageUrl;
  return updateProduct(editing.id, { ...readPayload(newUrl), etag: editing.etag });
}

function startEditKeepingValues(product) {
  editing = product;
  formTitle.textContent = `Editar ${product.name}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = imageInput.files[0] ?? null;
  if (file) {
    const problem = validateImage(file);
    if (problem) {
      showMessage(feedback, problem);
      return;
    }
  }
  const restore = setBusy(submit, "Guardando…");
  try {
    const saved = await save(file);
    upsertLocal(saved);
    dialog.close();
    showMessage(listFeedback, "Producto guardado.", "success");
  } catch (error) {
    if (error instanceof UploadError) {
      showMessage(feedback, `${error.message} El producto no se guardó con la nueva imagen.`);
    } else if (error instanceof ApiError) {
      showMessage(feedback, error.message);
    } else {
      throw error;
    }
  } finally {
    restore();
  }
});

document.getElementById("add-variant").addEventListener("click", () => addVariantRow());
resetButton.addEventListener("click", () => dialog.close());
closeDialogOnBackdropClick(dialog);
createButtonElement.addEventListener("click", (event) => openDialog(event.currentTarget));
// Fires for Esc, Cancelar and a successful save. A save re-renders the rows, so the original
// trigger may be detached: look its replacement up by product id.
dialog.addEventListener("close", () => {
  const target = dialogTrigger?.isConnected
    ? dialogTrigger
    : (editing && list.querySelector(`[data-edit-id="${CSS.escape(editing.id)}"]`)) ||
      createButtonElement;
  target.focus();
});

if (requireAdmin(panel, guardMessage)) {
  loadProducts();
}
