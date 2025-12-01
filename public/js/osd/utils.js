// Utils untuk viewer OSD

export function fitAndLockMinZoom(viewer) {
  if (!viewer.world.getItemCount()) return;
  const b = viewer.world.getHomeBounds();
  viewer.viewport.fitBounds(b, true);

  const fitZoom = viewer.viewport.getHomeZoom();
  viewer.viewport.minZoomLevel = fitZoom;

  if (viewer.viewport.getZoom() < fitZoom) {
    viewer.viewport.zoomTo(fitZoom, null, true);
  }
}