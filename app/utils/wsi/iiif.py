# wsi/iiif.py
import math


class IIIFInfoBuilder:
    """
    Build IIIF info.json dari WSI metadata.
    """

    def __init__(self, explorer):
        self.explorer = explorer

    def build(self):
        summary = self.explorer.summary()
        base = next((s for s in summary if s["iiif_ready"]), None)
        if not base:
            raise ValueError("No level IFD already to IIIF (no tiles).")

        w = base["width"]
        h = base["height"]
        tw = base["tileWidth"]
        th = base["tileLength"]

        scale = []
        for s in summary:
            if s["width"] and s["height"]:
                f = round(max(w / s["width"], h / s["height"]))
                scale.append(max(1, int(f)))

        scale = sorted(set(scale))

        levels = [{"width": s["width"], "height": s["height"]}
                  for s in summary if s["width"]]

        return {
            "@context": "http://iiif.io/api/image/2/context.json",
            "width": w,
            "height": h,
            "tiles": [{"width": tw, "scaleFactors": scale}],
            "levels": levels,
            "scaleFactors": scale
        }


class ZoomLevelBuilder:
    def build(self, info):
        """
        zoomlevel.json sesuai format kamu sebelumnya.
        """
        return {
            "tileWidth": info.get("tiles", [{}])[0].get("width"),
            "tileHeight": info.get("tiles", [{}])[0].get("height", info.get("tileHeight")),
            "scaleFactors": info["scaleFactors"],
            "levels": info["levels"]
        }

