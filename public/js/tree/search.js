export function bindSearch(treeEl, searchEl) {
  if (!treeEl || !searchEl) return;

  searchEl.addEventListener("input", () => {
    const q = searchEl.value.trim().toLowerCase();

    treeEl.querySelectorAll(".tree__node").forEach((n) => {
      if (n.dataset.folder !== undefined) return; // jangan sembunyikan label folder
      const li = n.parentElement;
      const match = n.textContent.trim().toLowerCase().includes(q);
      li.style.display = match ? "" : "none";
    });

    const any = q.length > 0;
    treeEl.querySelectorAll('.tree__node[data-folder]').forEach((f) => {
      if (any) f.classList.add("expanded");
      f.setAttribute("aria-expanded", String(f.classList.contains("expanded")));
      const kids = f.nextElementSibling;
      if (kids && kids.classList.contains("tree__children")) {
        kids.style.display = f.classList.contains("expanded") ? "block" : "none";
      }
    });
  });
}
