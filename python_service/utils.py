"""
utils.py - General Utility and Helper Functions.
Handles image conversions, base64 encoding, temporary file cleanup, and safe logging.
"""

import os
import io
import json
import base64
import logging
import tempfile
from typing import Optional, Any
import cv2
import numpy as np
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("IDExtractor")


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Converts a PIL Image object to an OpenCV BGR NumPy array."""
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    rgb_array = np.array(pil_image)
    return rgb_array[:, :, ::-1].copy()


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """Converts an OpenCV BGR or Grayscale NumPy array to PIL Image."""
    if len(cv2_image.shape) == 2:
        return Image.fromarray(cv2_image)
    rgb_array = cv2_image[:, :, ::-1]
    return Image.fromarray(rgb_array)


def cv2_to_base64(cv2_image: np.ndarray, format: str = "JPEG", quality: int = 70, max_dim: int = 1000) -> str:
    """
    Encodes an OpenCV image to an optimized base64 Data URL string.
    Downscales preview dimensions to keep JSON payload lightweight and fast (< 150KB).
    """
    h, w = cv2_image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        resized = cv2.resize(cv2_image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    else:
        resized = cv2_image

    pil_img = cv2_to_pil(resized)
    buf = io.BytesIO()
    if format.upper() == "JPEG":
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        pil_img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def safe_mask_log(text: str) -> str:
    """Masks potential Aadhaar numbers in logs."""
    import re
    return re.sub(r"\b(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\b", r"****-****-\3", text)


def format_json_output(data: Any, indent: int = 2) -> str:
    """Serializes a Pydantic model or dict to formatted JSON string."""
    if hasattr(data, "model_dump"):
        obj = data.model_dump()
    elif hasattr(data, "dict"):
        obj = data.dict()
    else:
        obj = data
    return json.dumps(obj, indent=indent, ensure_ascii=False)
