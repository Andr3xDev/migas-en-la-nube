import { apiFetch, ApiError } from "../api.js";
import { createProductImage, formatPeso, showMessage } from "../format.js";
import { requireAdmin } from "./guard.js";

const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGE_BYTES = 2 * 1024 * 1024;

const panel = document.getElementById("panel");
const guardMessage = document.getElementById("guard-message");
const list = document.getElementById("product-list");
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

function createButton(label, onClick, variant = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `button ${variant}`.trim();
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function createCell(content) {
  const cell = document.createElement("td");
  cell.append(content);
  return cell;
}

function describeVariants(product) {
  return product.variants
    .map((variant) => `${variant.name}: ${formatPeso(variant.price)} (stock ${variant.stock})`)
    .join("; ");
}

function renderList() {
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
    actions.append(
      createButton("Editar", () => startEdit(product), "button-secondary"),
      createButton("Eliminar", () => removeProduct(product), "button-danger"),
    );
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
  resetButton.hidden = true;
  renderCurrentImage();
}

function startEdit(product) {
  editing = product;
  HTMLFormElement.prototype.reset.call(form);
  form.elements.name.value = product.name;
  form.elements.category.value = product.category;
  form.elements.description.value = product.description;
  form.elements.prepMinutes.value = String(product.prepMinutes);
  variantsContainer.replaceChildren();
  for (const variant of product.variants) addVariantRow(variant);
  formTitle.textContent = `Editar ${product.name}`;
  resetButton.hidden = false;
  renderCurrentImage();
  feedback.replaceChildren();
}

function validateImage(file) {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return "La imagen debe ser JPEG, PNG o WebP.";
  if (file.size > MAX_IMAGE_BYTES) return "La imagen no puede superar 2 MB.";
  return null;
}

class UploadError extends Error {}

async function uploadImage(productId, file) {
  const { uploadUrl, imageUrl } = await apiFetch(`/api/admin/products/${productId}/image-upload-url`, {
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
    throw new UploadError("No se pudo subir la imagen.");
  }
  if (!response.ok) throw new UploadError("No se pudo subir la imagen.");
  return imageUrl;
}

async function loadProducts() {
  try {
    products = await apiFetch("/api/products");
    renderList();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(list, error.message);
  }
}

async function removeProduct(product) {
  if (!window.confirm(`¿Eliminar "${product.name}"?`)) return;
  try {
    await apiFetch(`/api/admin/products/${product.id}`, { method: "DELETE" });
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showMessage(feedback, error.message);
    return;
  }
  if (editing && editing.id === product.id) resetForm();
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

async function save(file) {
  const imageUrl = editing ? editing.imageUrl : null;
  let saved;
  if (!editing) {
    saved = await apiFetch("/api/admin/products", { method: "POST", body: readPayload(imageUrl) });
    upsertLocal(saved);
    if (!file) return saved;
    try {
      const newUrl = await uploadImage(saved.id, file);
      saved = await apiFetch(`/api/admin/products/${saved.id}`, {
        method: "PUT",
        body: readPayload(newUrl),
      });
    } catch (error) {
      // The product exists already: keep the form in edit mode so the upload can be retried.
      startEditKeepingValues(saved);
      throw error;
    }
    return saved;
  }
  const newUrl = file ? await uploadImage(editing.id, file) : imageUrl;
  return apiFetch(`/api/admin/products/${editing.id}`, { method: "PUT", body: readPayload(newUrl) });
}

function startEditKeepingValues(product) {
  editing = product;
  formTitle.textContent = `Editar ${product.name}`;
  resetButton.hidden = false;
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
  submit.disabled = true;
  try {
    const saved = await save(file);
    upsertLocal(saved);
    resetForm();
    showMessage(feedback, "Producto guardado.", "success");
  } catch (error) {
    if (error instanceof UploadError) {
      showMessage(feedback, `${error.message} El producto no se guardó con la nueva imagen.`);
    } else if (error instanceof ApiError) {
      showMessage(feedback, error.message);
    } else {
      throw error;
    }
  } finally {
    submit.disabled = false;
  }
});

document.getElementById("add-variant").addEventListener("click", () => addVariantRow());
resetButton.addEventListener("click", resetForm);

if (requireAdmin(panel, guardMessage)) {
  resetForm();
  loadProducts();
}
