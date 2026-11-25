// Icons are CSS masks (see .icon in styles.css): the CSP forbids inline SVG styling and
// <img> icons cannot inherit the text color.
export function createIcon(name) {
  const icon = document.createElement("span");
  icon.className = `icon icon-${name}`;
  icon.setAttribute("aria-hidden", "true");
  return icon;
}

// Without `text` the button is icon-only and `label` becomes its accessible name; with `text`
// the caller sets any aria-label itself.
export function createIconButton({ icon, label, text, variant = "secondary", onClick }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `button button-${variant}${text ? "" : " button-icon"}`;
  button.append(createIcon(icon));
  if (text) button.append(text);
  else button.setAttribute("aria-label", label);
  if (onClick) button.addEventListener("click", onClick);
  return button;
}

export function createIconLink({ icon, text, href, variant = "primary" }) {
  const link = document.createElement("a");
  link.className = `button button-${variant}`;
  link.href = href;
  link.append(createIcon(icon), text);
  return link;
}
