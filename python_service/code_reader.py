"""
code_reader.py - High-Performance Multi-Pass Barcode & QR Code Reader.
Uses zxing-cpp as primary local detector across all shipping symbologies:
(QR Code, Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E, ITF, Data Matrix, Aztec, PDF417).
Features 5 progressive detection passes (Original, Enhanced CLAHE/Sharpen, Otsu/Adaptive Thresholding,
Multi-Angle Rotations 90°/180°/270°, and OpenCV QRCodeDetector fallback).
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


def _scan_zxing(image: np.ndarray) -> List[Tuple[str, str]]:
    """Runs zxingcpp barcode and QR detection on an image array."""
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
                found.append((fmt, val))
    except Exception:
        pass
    return found


def _scan_opencv_qr(image: np.ndarray) -> List[Tuple[str, str]]:
    """Pass 5 Fallback scanner using OpenCV QRCodeDetector."""
    found = []
    if image is None or image.size == 0:
        return found
    try:
        detector = cv2.QRCodeDetector()
        # Multi QR detection attempt
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(image)
        if retval and decoded_info:
            for text in decoded_info:
                val = text.strip() if text else ""
                if val:
                    found.append(("QRCode", val))
        else:
            # Single QR detect attempt
            val, points, _ = detector.detectAndDecode(image)
            if val and val.strip():
                found.append(("QRCode", val.strip()))
    except Exception:
        pass
    return found


def extract_codes(image: np.ndarray) -> Dict[str, List[Dict[str, Any]]]:
    """
    Multi-pass Barcode and QR code extractor with progressive enhancement:
    - Pass 1: Original image directly via zxing-cpp
    - Pass 2: Grayscale -> Upscale -> CLAHE -> Sharpening retry
    - Pass 3: Otsu and Adaptive Gaussian Thresholding retry
    - Pass 4: Multi-Angle Rotations (90°, 180°, 270°) retry
    - Pass 5: OpenCV QRCodeDetector fallback
    
    Returns separate arrays for 'barcodes' and 'qr_codes', deduplicated by (format, value).
    """
    if image is None or image.size == 0:
        return {"barcodes": [], "qr_codes": []}

    seen_keys: Set[Tuple[str, str]] = set()
    raw_results: List[Tuple[str, str]] = []

    def record_codes(codes: List[Tuple[str, str]]):
        for fmt, val in codes:
            clean_val = val.strip()
            if not clean_val:
                continue
            key = (fmt, clean_val)
            if key not in seen_keys:
                seen_keys.add(key)
                raw_results.append((fmt, clean_val))

    # =========================================================================
    # PASS 1: Native image scan
    # =========================================================================
    record_codes(_scan_zxing(image))

    # Prepare grayscale base for Passes 2-4
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # =========================================================================
    # PASS 2: Grayscale -> Upscale -> CLAHE -> Sharpen retry
    # =========================================================================
    if len(raw_results) == 0:
        try:
            h, w = gray.shape[:2]
            upscaled = cv2.resize(gray, (int(w * 1.5), int(h * 1.5)), interpolation=cv2.INTER_CUBIC)

            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            clahe_img = clahe.apply(upscaled)

            # Sharpening kernel
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(clahe_img, -1, kernel)

            record_codes(_scan_zxing(sharpened))
            if len(raw_results) == 0:
                record_codes(_scan_zxing(clahe_img))
        except Exception:
            pass

    # =========================================================================
    # PASS 3: Threshold Processing (Otsu & Adaptive Gaussian)
    # =========================================================================
    if len(raw_results) == 0:
        try:
            # Otsu Thresholding
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            record_codes(_scan_zxing(otsu))

            # Adaptive Gaussian Thresholding
            if len(raw_results) == 0:
                adaptive = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
                )
                record_codes(_scan_zxing(adaptive))
        except Exception:
            pass

    # =========================================================================
    # PASS 4: Rotation Detection (90°, 180°, 270°)
    # =========================================================================
    if len(raw_results) == 0:
        try:
            for rot_code in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                rotated = cv2.rotate(image, rot_code)
                record_codes(_scan_zxing(rotated))
                if len(raw_results) > 0:
                    break
        except Exception:
            pass

    # =========================================================================
    # PASS 5: OpenCV QRCodeDetector Fallback
    # =========================================================================
    has_qr = any(_is_qr_or_matrix_format(fmt) for fmt, _ in raw_results)
    if not has_qr:
        record_codes(_scan_opencv_qr(image))
        if not any(_is_qr_or_matrix_format(fmt) for fmt, _ in raw_results):
            # Try OpenCV on rotated angles
            for rot_code in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                rotated = cv2.rotate(image, rot_code)
                record_codes(_scan_opencv_qr(rotated))
                if any(_is_qr_or_matrix_format(fmt) for fmt, _ in raw_results):
                    break

    # =========================================================================
    # Partition into Barcodes vs QR Codes with Content Classification
    # =========================================================================
    barcodes = []
    qr_codes = []

    for fmt, val in raw_results:
        is_matrix = _is_qr_or_matrix_format(fmt)
        classification = classify_qr_content(val)
        item = {
            "format": fmt,
            "value": val,
            "content_type": classification
        }
        if is_matrix:
            qr_codes.append(item)
        else:
            barcodes.append(item)

    return {
        "barcodes": barcodes,
        "qr_codes": qr_codes
    }

