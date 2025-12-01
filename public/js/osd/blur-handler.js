// Blur kompatibel WebGL & Canvas (tanpa 'tile-drawing')
export function setupBlurHandler(viewer, osdEl, idleMs = 120) {
  let blurTimer;

  const setBlur = (on) => osdEl.classList.toggle("blurring", !!on);
  const scheduleBlurOff = () => {
    clearTimeout(blurTimer);
    blurTimer = setTimeout(() => setBlur(false), idleMs);
  };

  viewer.addHandler("update-viewport", function () {
    setBlur(true);
    scheduleBlurOff();
  });

  viewer.addHandler("tile-loaded", scheduleBlurOff);
  viewer.addHandler("tile-load-failed", scheduleBlurOff);

  viewer.addHandler("open", function () {
    setBlur(true);
    scheduleBlurOff();
  });
}