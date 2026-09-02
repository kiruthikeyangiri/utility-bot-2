"""
ocr_engine.py - ONNX-powered Optical Character Recognition Module (RapidOCR).
Provides fast, local, dependency-free OCR without requiring Tesseract or external binaries.
Extracts text tokens with bounding boxes, spatial coordinates, and confidence scores,
and draws visual bounding box overlays on images.
"""

import os
from typing import List, Tuple, Optional
import cv2
import numpy as np
from dotenv import load_dotenv

from schemas import BoundingBox, OCRResult

load_dotenv()

# Singleton RapidOCR engine instance
_rapid_ocr_engine = None


def get_ocr_engine():
    """Initializes or returns cached RapidOCR instance."""
    global _rapid_ocr_engine
    if _rapid_ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _rapid_ocr_engine = RapidOCR()
    return _rapid_ocr_engine


def check_ocr_available() -> Tuple[bool, str]:
    """Verifies whether RapidOCR is accessible."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        return True, "RapidOCR ONNX Runtime Deep Learning Engine active (No external binary required)."
    except Exception as e:
        return False, f"OCR Engine not available: {str(e)}"


# Backward compatibility aliases
check_tesseract_available = check_ocr_available
get_ocr_reader = get_ocr_engine


def extract_ocr_data(
    image: np.ndarray,
    min_confidence: float = 25.0,
    psm_mode: Optional[int] = None,
    lang: str = "en"
) -> OCRResult:
    """
    Executes RapidOCR to retrieve detected text, bounding boxes, and confidence scores.
    Sorts detected text blocks spatially and groups them into lines.
    """
    is_avail, msg = check_ocr_available()
    if not is_avail:
        raise RuntimeError(f"OCR engine is not available: {msg}")

    engine = get_ocr_engine()

    # Ensure valid 3-channel BGR format for OCR
    if len(image.shape) == 2:
        img_for_ocr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        img_for_ocr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        img_for_ocr = image.copy()

    # Execute OCR inference
    ocr_results, _ = engine(img_for_ocr)

    words: List[BoundingBox] = []
    total_conf = 0.0
    valid_count = 0

    if ocr_results:
        # Sort results spatially by top Y coordinate then left X coordinate
        sorted_results = sorted(
            ocr_results,
            key=lambda item: (min(pt[1] for pt in item[0]), min(pt[0] for pt in item[0]))
        )

        for box, text_raw, conf_val in sorted_results:
            text = str(text_raw).strip()
            try:
                conf_pct = round(float(conf_val) * 100, 2)
            except (ValueError, TypeError):
                conf_pct = 80.0

            # Skip empty strings or low confidence noise
            if not text or conf_pct < min_confidence:
                continue

            x_min = int(min(pt[0] for pt in box))
            y_min = int(min(pt[1] for pt in box))
            x_max = int(max(pt[0] for pt in box))
            y_max = int(max(pt[1] for pt in box))
            w = max(1, x_max - x_min)
            h = max(1, y_max - y_min)

            # Filter out tiny noise specks
            if w < 4 or h < 5:
                continue

            # Ignore junk single character non-alphanumerics
            if len(text) == 1 and not text.isalnum() and text not in ['-', '/', ':', '#']:
                continue

            bbox = BoundingBox(
                text=text,
                confidence=conf_pct,
                x=x_min,
                y=y_min,
                width=w,
                height=h
            )
            words.append(bbox)
            total_conf += conf_pct
            valid_count += 1

    # Group words into approximate spatial lines (threshold based on box height)
    lines: List[List[BoundingBox]] = []
    for word in words:
        placed = False
        for line in lines:
            line_avg_y = sum(w.y for w in line) / len(line)
            line_avg_h = sum(w.height for w in line) / len(line)
            if abs(word.y - line_avg_y) <= (line_avg_h * 0.6):
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])

    # Sort words within each line from left to right
    raw_lines = []
    layout_lines = []
    for line in lines:
        line.sort(key=lambda w: w.x)
        line_str = " ".join([w.text for w in line])
        raw_lines.append(line_str)
        min_x = min(w.x for w in line)
        min_y = min(w.y for w in line)
        layout_lines.append(f"TEXT: {line_str}\nPOSITION: x={min_x}, y={min_y}")

    raw_text = "\n".join(raw_lines)
    layout_text = "\n\n".join(layout_lines)
    avg_conf = round(total_conf / valid_count, 2) if valid_count > 0 else 0.0

    return OCRResult(
        words=words,
        raw_text=raw_text,
        layout_text=layout_text,
        average_confidence=avg_conf,
        word_count=valid_count
    )


def draw_bounding_boxes(
    image: np.ndarray,
    ocr_result: OCRResult,
    show_confidence: bool = True
) -> np.ndarray:
    """Draws color-coded bounding boxes and confidence tags around detected text."""
    annotated = image.copy()
    if len(annotated.shape) == 2:
        annotated = cv2.cvtColor(annotated, cv2.COLOR_GRAY2BGR)

    for word in ocr_result.words:
        x, y, w, h = word.x, word.y, word.width, word.height

        # Color coding: Green if confidence > 75, Orange if 50-75, Yellow if < 50
        if word.confidence >= 75:
            current_box_color = (0, 200, 0)
        elif word.confidence >= 50:
            current_box_color = (0, 165, 255)
        else:
            current_box_color = (0, 255, 255)

        # Draw bounding rectangle
        cv2.rectangle(annotated, (x, y), (x + w, y + h), current_box_color, 2)

        # Draw small confidence score above box if requested
        if show_confidence:
            label = f"{int(word.confidence)}%"
            font_scale = 0.4
            thickness = 1
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            cv2.rectangle(annotated, (x, max(0, y - th - 4)), (x + tw + 2, max(th + 4, y)), current_box_color, -1)
            cv2.putText(
                annotated,
                label,
                (x + 1, max(th, y - 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 0, 0),
                thickness,
                cv2.LINE_AA
            )

    return annotated
