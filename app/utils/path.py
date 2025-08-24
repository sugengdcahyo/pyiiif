import os
from pathlib import Path
from flask import abort


def safe_join_slide(slide_root: Path, image_id: str) -> str:
    iid = image_id.lstrip("/").replace("\\", "/")
    if ".." in iid:
        abort(400, description="Invalid identifier")
    candidate = (slide_root / iid).resolve()
    if not (str(candidate) == str(slide_root) or
            str(candidate).startswith(str(slide_root) + os.sep)):
        abort(400, description="Invalid identifier")
    return str(candidate)
