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

// Scrolls both axes; focusable so keyboard users can scroll it.
export function createTableScroller(table, label) {
  const scroller = document.createElement("div");
  scroller.className = "table-scroll";
  scroller.tabIndex = 0;
  scroller.setAttribute("role", "region");
  scroller.setAttribute("aria-label", label);
  scroller.append(table);
  return scroller;
}

export function createTableHead(headings) {
  const head = document.createElement("thead");
  const row = document.createElement("tr");
  for (const label of headings) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    row.append(cell);
  }
  head.append(row);
  return head;
}
