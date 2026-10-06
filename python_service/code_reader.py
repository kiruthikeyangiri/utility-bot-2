"""
code_reader.py - High-Performance Multi-Pass Barcode & QR Code Reader.
Uses zxing-cpp as primary local detector across all shipping symbologies:
(QR Code, Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E, ITF, Data Matrix, Aztec, PDF417).
Features 6 progressive detection passes (Original, Multi-Scale Upscaling, Regional Bands,
Enhanced CLAHE/Sharpen/Otsu/Adaptive Thresholding, Multi-Angle Rotations 90°/180°/270°,
and OpenCV QRCodeDetector fallback).
Captures spatial bounding polygon / coordinate metadata for all detected codes.
Classifies QR content (Tracking URL, AWB, Order ID, Shipment ID, JSON, Courier Info, Plain Text).
Deduplicates all detected codes using (format, value).
"""

import json
import re
from typing import Dict, List, Any, Set, Tuple, Optional
import cv2
import numpy as np

try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False


def _is_qr_or_matrix_format(format_name: str) -> bool:
    """Identifies if a format name corresponds to a 2D matrix or QR code variation."""
    fn = format_name.upper().replace(" ", "").replace("-", "").replace("_", "")
    return "QR" in fn or "AZTEC" in fn or "DATAMATRIX" in fn or "MAXICODE" in fn


def classify_qr_content(val: str) -> str:
    """
    Classifies the decoded value of a QR code into functional logistics categories:
    - Tracking URL
    - AWB Number
    - Shipment ID
    - Order ID
    - Courier Information
    - JSON
    - Plain Text
    - Unknown
    """
    if not val:
        return "Unknown"
    v = val.strip()

    # 1. URL / Tracking Link Check
    if re.match(r"^https?://", v, re.IGNORECASE) or re.match(r"^www\.", v, re.IGNORECASE):
        return "Tracking URL"

    # 2. JSON Payload Check
    if (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]")):
        try:
            json.loads(v)
            return "JSON"
        except Exception:
            pass

    # 3. Order ID Check
    if re.match(r"^(?:ORD|ORDER|#|PO)[-_0-9A-Za-z]+$", v, re.IGNORECASE):
        return "Order ID"

    # 4. Shipment / Consignment ID Check
    if re.match(r"^(?:SHP|SHIP|SHIPMENT|CONSIGNMENT)[-_0-9A-Za-z]+$", v, re.IGNORECASE):
        return "Shipment ID"

    # 5. AWB / Tracking Number Check (e.g. 10-35 digits or AWB-prefixed)
    if re.search(r"\b(?:AWB|AIR\s*WAYBILL)\b", v, re.IGNORECASE) or re.match(r"^[0-9]{8,35}$", v):
        return "AWB Number"

    # 6. Courier brand information
    if any(k in v.upper() for k in ["FEDEX", "USPS", "UPS", "DELHIVERY", "BLUE DART", "DHL", "DTDC", "AMAZON", "EKART"]):
        return "Courier Information"

    # 7. Generic Plain Text vs. Unknown
    if len(v) < 200:
        return "Plain Text"
    return "Unknown"


def _map_point_to_original(
    px: float,
    py: float,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
    rotation: int = 0,
    orig_w: int = 0,
    orig_h: int = 0
) -> Dict[str, int]:
    """Transforms a point from transformed image space back to original image space."""
    # 1. Reverse rotation if applied
    if rotation == 90:
        # 90 clockwise: x_orig = py, y_orig = orig_h - 1 - px
        x = py
        y = orig_h - 1 - px
    elif rotation == 180:
        x = orig_w - 1 - px
        y = orig_h - 1 - py
    elif rotation == 270:
        x = orig_w - 1 - py
        y = px
    else:
        x = px
        y = py

    # 2. Reverse scaling and offset
    x = (x / scale) + offset_x
    y = (y / scale) + offset_y

    return {"x": int(round(x)), "y": int(round(y))}


def _scan_zxing(
    image: np.ndarray,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
    rotation: int = 0,
    orig_w: int = 0,
    orig_h: int = 0
) -> List[Tuple[str, str, List[Dict[str, int]]]]:
    """Runs zxingcpp barcode and QR detection on an image array and maps position back to original image space."""
    if not HAS_ZXING or image is None or image.size == 0:
        return []

    found = []
    try:
        results = zxingcpp.read_barcodes(image)
        for res in results:
            val = (res.text or "").strip()
            if val:
                fmt = getattr(res.format, "name", str(res.format))
                if "BarcodeFormat." in fmt:
                    fmt = fmt.replace("BarcodeFormat.", "")
                fmt = fmt.replace(" ", "")

                pos_list = []
                if hasattr(res, "position") and res.position:
                    pts = [res.position.top_left, res.position.top_right, res.position.bottom_right, res.position.bottom_left]
                    for pt in pts:
                        mapped = _map_point_to_original(
                            pt.x, pt.y,
                            scale=scale,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            rotation=rotation,
                            orig_w=orig_w,
                            orig_h=orig_h
                        )
                        pos_list.append(mapped)

                found.append((fmt, val, pos_list))
    except Exception:
        pass
    return found


def _scan_opencv_qr(
    image: np.ndarray,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
    rotation: int = 0,
    orig_w: int = 0,
    orig_h: int = 0
) -> List[Tuple[str, str, List[Dict[str, int]]]]:
    """Pass 6 Fallback scanner using OpenCV QRCodeDetector."""
    found = []
    if image is None or image.size == 0:
        return found
    try:
        detector = cv2.QRCodeDetector()
        # Multi QR detection attempt
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(image)
        if retval and decoded_info:
            for idx, text in enumerate(decoded_info):
                val = text.strip() if text else ""
                if val:
                    pos_list = []
                    if points is not None and len(points) > idx:
                        for pt in points[idx]:
                            mapped = _map_point_to_original(
                                pt[0], pt[1],
                                scale=scale,
                                offset_x=offset_x,
                                offset_y=offset_y,
                                rotation=rotation,
                                orig_w=orig_w,
                                orig_h=orig_h
                            )
                            pos_list.append(mapped)
                    found.append(("QRCode", val, pos_list))
        else:
            # Single QR detect attempt
            val, points, _ = detector.detectAndDecode(image)
            if val and val.strip():
                pos_list = []
                if points is not None:
                    pts = points[0] if len(points.shape) == 3 else points
                    for pt in pts:
                        mapped = _map_point_to_original(
                            pt[0], pt[1],
                            scale=scale,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            rotation=rotation,
                            orig_w=orig_w,
                            orig_h=orig_h
                        )
                        pos_list.append(mapped)
                found.append(("QRCode", val.strip(), pos_list))
    except Exception:
        pass
    return found


def extract_codes(image: np.ndarray) -> Dict[str, List[Dict[str, Any]]]:
    """
    High-Precision Multi-Pass Barcode and QR code extractor.
    Scans for ALL codes present on single or multi-code shipping documents:
    - Pass 1: Native image scan via zxing-cpp
    - Pass 2: Multi-Scale Full Image Scans (1.5x, 2.0x upscale for fine 1D bars)
    - Pass 3: Regional Band Scans (Top 60%, Bottom 60%, Upscaled lower tracking zone)
    - Pass 4: Grayscale -> CLAHE -> Sharpening & Otsu Binarization
    - Pass 5: Multi-Angle Rotations (90°, 180°, 270°)
    - Pass 6: OpenCV QRCodeDetector Fallback
    
    Returns separate arrays for 'barcodes' and 'qr_codes', deduplicated by (format, value),
    with spatial polygon coordinates preserved.
    """
    if image is None or image.size == 0:
        return {"barcodes": [], "qr_codes": []}

    orig_h, orig_w = image.shape[:2]
    seen_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def record_codes(codes: List[Tuple[str, str, List[Dict[str, int]]]]):
        for fmt, val, pos in codes:
            clean_val = val.strip()
            if not clean_val:
                continue
            key = (fmt, clean_val)
            if key not in seen_dict:
                seen_dict[key] = {
                    "format": fmt,
                    "value": clean_val,
                    "content_type": classify_qr_content(clean_val),
                    "position": pos if pos else None
                }
            elif not seen_dict[key].get("position") and pos:
                seen_dict[key]["position"] = pos

    # =========================================================================
    # PASS 1: Native full image scan
    # =========================================================================
    record_codes(_scan_zxing(image, orig_w=orig_w, orig_h=orig_h))

    # =========================================================================
    # PASS 2: Multi-Scale Upscaling (1.5x & 2.0x) - Crucial for fine 1D bars
    # =========================================================================
    for scale in [1.5, 2.0]:
        try:
            upscaled = cv2.resize(image, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_CUBIC)
            record_codes(_scan_zxing(upscaled, scale=scale, orig_w=orig_w, orig_h=orig_h))
        except Exception:
            pass

    # =========================================================================
    # PASS 3: Regional Band Scans (Top band, Bottom band, Upscaled bottom band)
    # =========================================================================
    try:
        # Top 60% (Postage stamps, top 2D DataMatrix/QR codes)
        top_band = image[:int(orig_h * 0.6), :]
        record_codes(_scan_zxing(top_band, offset_y=0, orig_w=orig_w, orig_h=orig_h))

        # Bottom 60% (Shipping tracking 1D barcodes)
        bottom_offset_y = int(orig_h * 0.45)
        bottom_band = image[bottom_offset_y:, :]
        record_codes(_scan_zxing(bottom_band, offset_y=bottom_offset_y, orig_w=orig_w, orig_h=orig_h))

        # Upscaled bottom band
        bh, bw = bottom_band.shape[:2]
        b_upscaled = cv2.resize(bottom_band, (int(bw * 1.5), int(bh * 1.5)), interpolation=cv2.INTER_CUBIC)
        record_codes(_scan_zxing(b_upscaled, scale=1.5, offset_y=bottom_offset_y, orig_w=orig_w, orig_h=orig_h))
    except Exception:
        pass

    # =========================================================================
    # PASS 4: Grayscale + CLAHE + Sharpening + Thresholding
    # =========================================================================
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        clahe_img = clahe.apply(gray)
        record_codes(_scan_zxing(clahe_img, orig_w=orig_w, orig_h=orig_h))

        # Sharpening kernel
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(clahe_img, -1, kernel)
        record_codes(_scan_zxing(sharpened, orig_w=orig_w, orig_h=orig_h))

        # Otsu thresholding
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        record_codes(_scan_zxing(otsu, orig_w=orig_w, orig_h=orig_h))

        # Adaptive Gaussian Thresholding
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
        )
        record_codes(_scan_zxing(adaptive, orig_w=orig_w, orig_h=orig_h))
    except Exception:
        pass

    # =========================================================================
    # PASS 5: Multi-Angle Rotations (90°, 180°, 270°)
    # =========================================================================
    if len(seen_dict) == 0:
        try:
            for rot_code, rot_deg in [
                (cv2.ROTATE_90_CLOCKWISE, 90),
                (cv2.ROTATE_180, 180),
                (cv2.ROTATE_90_COUNTERCLOCKWISE, 270)
            ]:
                rotated = cv2.rotate(image, rot_code)
                record_codes(_scan_zxing(rotated, rotation=rot_deg, orig_w=orig_w, orig_h=orig_h))
        except Exception:
            pass

    # =========================================================================
    # PASS 6: OpenCV QRCodeDetector Fallback
    # =========================================================================
    has_qr = any(_is_qr_or_matrix_format(fmt) for (fmt, _) in seen_dict.keys())
    if not has_qr:
        record_codes(_scan_opencv_qr(image, orig_w=orig_w, orig_h=orig_h))
        if not any(_is_qr_or_matrix_format(fmt) for (fmt, _) in seen_dict.keys()):
            for rot_code, rot_deg in [
                (cv2.ROTATE_90_CLOCKWISE, 90),
                (cv2.ROTATE_180, 180),
                (cv2.ROTATE_90_COUNTERCLOCKWISE, 270)
            ]:
                rotated = cv2.rotate(image, rot_code)
                record_codes(_scan_opencv_qr(rotated, rotation=rot_deg, orig_w=orig_w, orig_h=orig_h))
                if any(_is_qr_or_matrix_format(fmt) for (fmt, _) in seen_dict.keys()):
                    break

    # =========================================================================
    # Partition into Barcodes vs QR Codes with Content Classification
    # =========================================================================
    barcodes = []
    qr_codes = []

    for item in seen_dict.values():
        if _is_qr_or_matrix_format(item["format"]):
            qr_codes.append(item)
        else:
            barcodes.append(item)

    return {
        "barcodes": barcodes,
        "qr_codes": qr_codes
    }
