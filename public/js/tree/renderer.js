export function renderTree(rootUL, nodes) {
  if (!rootUL || !Array.isArray(nodes)) return;
  nodes.forEach((node) => rootUL.appendChild(renderNode(node)));
}

export function renderNode(node) {
  const li = document.createElement("li");

  if (node.folder) {
    const div = document.createElement("div");
    div.className = "tree__node";
    div.setAttribute("role", "treeitem");
    div.dataset.folder = "";
    if (node.expanded) div.classList.add("expanded");
    div.setAttribute("aria-expanded", String(!!node.expanded));

    const caret = document.createElement("span");
    caret.className = "tree__caret"; caret.textContent = "▸";

    const icon = document.createElement("svg");
    icon.className = "tree__icon"; icon.setAttribute("viewBox","0 0 16 16");
    icon.innerHTML = '<path fill="currentColor" d="M1 4h5l1 1h8v7H1z"/>';

    const label = document.createElement("span");
    label.textContent = node.name || "Folder";

    const ul = document.createElement("ul");
    ul.className = "tree__children";
    if (node.expanded) ul.style.display = "block";
    (node.children || []).forEach((ch) => ul.appendChild(renderNode(ch)));

    div.append(caret, icon, label);
    li.append(div, ul);
    return li;
  }

  // leaf
  const div = document.createElement("div");
  div.className = "tree__node";
  div.setAttribute("role", "treeitem");
  div.textContent = node.name || "Untitled";
  if (node.iiif) div.dataset.iiif = node.iiif;
  li.appendChild(div);
  return li;
}
