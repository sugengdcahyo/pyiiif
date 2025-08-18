import { fitAndLockMinZoom } from "./utils.js";
import { setupBlurHandler } from "./blur-handler.js";

export function initViewer(iiifUrl, osdEl, opts = {}) {
  const viewer = OpenSeadragon(Object.assign({
    id: "openseadragon",
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/5.0.1/images/",
    tileSources: iiifUrl,            // STRING URL ke info.json
    immediateRender: true,
    alwaysBlend: true,
    blendTime: 0.35,
    smoothTileEdgesMinZoom: Infinity,
    maxZoomPixelRatio: 1,
    visibilityRatio: 1.0,
    constrainDuringPan: true,
    loadTilesWithAjax: true,
    crossOriginPolicy: "Anonymous",
    imageLoaderLimit: 12,
    maxImageCacheCount: 512,
    showNavigator: true,
    showRotationControl: true
  }, opts));

  viewer.addHandler("open",  () => fitAndLockMinZoom(viewer));
  viewer.addHandler("resize",() => fitAndLockMinZoom(viewer));

  setupBlurHandler(viewer, osdEl);

  return viewer;
}
