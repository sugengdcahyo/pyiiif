import { initViewer }   from "./osd/viewer.js";
import { initTree }     from "./tree/tree.js";
import { initSidebar }  from "./ui/sidebar.js";

document.addEventListener("DOMContentLoaded", () => {
  const osdEl   = document.getElementById("openseadragon");
  const treeEl  = document.getElementById("tree");
  const searchEl= document.getElementById("tree-search");
  const appEl   = document.querySelector(".app");
  let   btnEl   = document.getElementById("btn-toggle-sidebar");

  if (!osdEl) {
    console.error("#openseadragon not found.");
    return;
  }

  // buat tombol sidebar jika belum ada di HTML
  if (!btnEl) {
    const bar = document.querySelector(".viewer__toolbar");
    if (bar) {
      btnEl = document.createElement("button");
      btnEl.id = "btn-toggle-sidebar";
      btnEl.className = "bx--btn bx--btn--ghost";
      btnEl.title = "Toggle sidebar";
      btnEl.textContent = "☰";
      bar.prepend(btnEl);
    }
  }

  // sumber awal IIIF
  const qsIIIF   = new URLSearchParams(location.search).get("iiif");
  const lastIIIF = localStorage.getItem("lastIiif");
  const DEFAULT_IIIF = "http://localhost:5050/iiif/CMU-1.svs/info.json";
  const IIIF_URL = qsIIIF || lastIIIF || DEFAULT_IIIF;

  // init viewer
  const viewer = initViewer(IIIF_URL, osdEl);

  // init tree (load dari JSON + interaksi)
  initTree(treeEl, viewer, {
    searchEl,
    sourcesUrl: "./iiif-sources/samples.json",
    inlineFallbackId: "iiif-sources-inline"
  });

  // init sidebar toggle
  initSidebar(appEl, btnEl, viewer);
});
