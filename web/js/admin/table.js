export function createCell(content, className = "") {
  const cell = document.createElement("td");
  cell.className = className;
  cell.append(content);
  return cell;
}

export function createButton(label, onClick, variant = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `button ${variant}`.trim();
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}
