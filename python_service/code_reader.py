"""
code_reader.py - High-Performance Barcode & QR Code Reader.
Uses zxing-cpp as primary detector with multi-pass image enhancement retries
and OpenCV QRCodeDetector fallback.
Deduplicates all detected codes using (format, value) tuple.
"""

from typing import Dict, List, Any, Set, Tuple
import cv2
import numpy as np

try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False


def _is_qr_format(format_name: str) -> bool:
    """Identifies if a format name corresponds to a QR code variation."""
    fn = format_name.upper().replace(" ", "").replace("-", "").replace("_", "")
    return "QR" in fn or "AZTEC" in fn or "DATAMATRIX" in fn


def _scan_zxing(image: np.ndarray) -> List[Tuple[str, str]]:
    """Runs zxingcpp barcode and QR detection on an image."""
    if not HAS_ZXING or image is None or image.size == 0:
        return []

    found = []
    try:
        # zxingcpp handles RGB/BGR numpy arrays
        results = zxingcpp.read_barcodes(image)
        for res in results:
            val = (res.text or "").strip()
            if val:
                fmt = getattr(res.format, "name", str(res.format))
                # Normalize format name string (e.g. 'BarcodeFormat.QRCode' -> 'QRCode')
                if "BarcodeFormat." in fmt:
                    fmt = fmt.replace("BarcodeFormat.", "")
                fmt = fmt.replace(" ", "")
                found.append((fmt, val))
    except Exception:
        pass
    return found


def _scan_opencv_qr(image: np.ndarray) -> List[Tuple[str, str]]:
    """Fallback scanner using OpenCV QRCodeDetector."""
    found = []
    try:
        detector = cv2.QRCodeDetector()
        # Try multi QR detection
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(image)
        if retval and decoded_info:
            for text in decoded_info:
                val = text.strip() if text else ""
                if val:
                    found.append(("QRCode", val))
        else:
            # Fallback to single QR detect
            val, points, _ = detector.detectAndDecode(image)
            if val and val.strip():
                found.append(("QRCode", val.strip()))
    except Exception:
        pass
    return found


def extract_codes(image: np.ndarray) -> Dict[str, List[Dict[str, str]]]:
    """
    Multi-pass Barcode and QR code extractor with progressive enhancement:
    Pass 1: Original image via zxing-cpp
    Pass 2: Grayscale -> Upscale -> CLAHE -> Sharpening retry
    Pass 3: Threshold variants & 90/180/270 degree rotation retry
    Pass 4: OpenCV QRCodeDetector fallback
    
    Deduplicates results so each code is returned only once.
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

    # =========================================================================
    # PASS 2: Grayscale -> Upscale -> CLAHE -> Sharpen retry
    # =========================================================================
    if len(raw_results) == 0:
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Upscale 1.5x for dense or small barcodes
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
    # PASS 3: Threshold variants & Rotation (90, 180, 270 degrees)
    # =========================================================================
    if len(raw_results) == 0:
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Otsu Thresholding
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            record_codes(_scan_zxing(otsu))

            # Adaptive Thresholding
            if len(raw_results) == 0:
                adaptive = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
                )
                record_codes(_scan_zxing(adaptive))

            # Rotations (Labels can be oriented horizontally or vertically)
            if len(raw_results) == 0:
                for rot_code in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                    rotated = cv2.rotate(image, rot_code)
                    record_codes(_scan_zxing(rotated))
                    if len(raw_results) > 0:
                        break
        except Exception:
            pass

    # =========================================================================
    # PASS 4: OpenCV QRCodeDetector Fallback
    # =========================================================================
    has_qr = any(_is_qr_format(fmt) for fmt, _ in raw_results)
    if not has_qr:
        record_codes(_scan_opencv_qr(image))

    # =========================================================================
    # Partition into Barcodes vs QR Codes
    # =========================================================================
    barcodes = []
    qr_codes = []

    for fmt, val in raw_results:
        item = {"format": fmt, "value": val}
        if _is_qr_format(fmt):
            qr_codes.append(item)
        else:
            barcodes.append(item)

    return {
        "barcodes": barcodes,
        "qr_codes": qr_codes
    }
