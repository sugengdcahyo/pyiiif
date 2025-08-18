import { renderTree } from "./renderer.js";
import { bindSearch } from "./search.js";

export async function initTree(treeEl, viewer, { searchEl, sourcesUrl, inlineFallbackId = "iiif-sources-inline" } = {}) {
  if (!treeEl) return;

  const nodes = await loadSources(sourcesUrl, inlineFallbackId);
  renderTree(treeEl, nodes);
  if (searchEl) bindSearch(treeEl, searchEl);

  treeEl.addEventListener("click", (e) => {
    const node = e.target.closest(".tree__node");
    if (!node) return;

    // folder toggle
    if (node.dataset.folder !== undefined) {
      node.classList.toggle("expanded");
      const expanded = node.classList.contains("expanded");
      node.setAttribute("aria-expanded", String(expanded));
      const kids = node.nextElementSibling;
      if (kids && kids.classList.contains("tree__children")) {
        kids.style.display = expanded ? "block" : "none";
      }
      return;
    }

    // presets (opsional, bila kamu pakai data-action)
    const action = node.dataset.action;
    if (action && viewer) {
      if (action === "fit" || action === "home") viewer.viewport.goHome(true);
      if (action === "1x") viewer.viewport.zoomTo(1.0, null, true);
      if (action === "2x") viewer.viewport.zoomTo(2.0, null, true);
    }

    // open IIIF
    const iiif = node.dataset.iiif;
    if (iiif && viewer) {
      viewer.open(iiif);
      localStorage.setItem("lastIiif", iiif);
      document.getElementById("openseadragon")?.classList.add("blurring");
    }

    // mark current
    treeEl.querySelectorAll('.tree__node[aria-current="true"]').forEach(n => n.removeAttribute("aria-current"));
    if (!node.dataset.folder) node.setAttribute("aria-current", "true");
  });
}

async function loadSources(sourcesUrl = "./iiif-sources/samples.json", inlineFallbackId) {
  try {
    const url = new URL(sourcesUrl, location.href).toString();
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Gagal memuat daftar dari JSON, fallback inline:", err);
    const inline = document.getElementById(inlineFallbackId);
    return inline ? JSON.parse(inline.textContent) : [];
  }
}
