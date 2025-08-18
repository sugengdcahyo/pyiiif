import { fitAndLockMinZoom } from "../osd/utils.js";

export function initSidebar(appEl, btnEl, viewer, { afterMs = 220 } = {}) {
  if (!appEl || !btnEl) return;

  btnEl.addEventListener("click", () => {
    appEl.classList.toggle("sidebar-collapsed");
    setTimeout(() => {
      if (viewer) fitAndLockMinZoom(viewer);
    }, afterMs);
  });
}
