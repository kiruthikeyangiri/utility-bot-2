"""
preprocessing.py - Image Preprocessing Module using OpenCV.
Provides modular image enhancement functions to optimize OCR accuracy
and assess image quality (blurriness, contrast).
"""

from typing import Tuple, Dict, Any
import cv2
import numpy as np


def assess_image_quality(image: np.ndarray, blur_threshold: float = 80.0) -> Dict[str, Any]:
    """
    Evaluates image quality metrics including blurriness via Laplacian variance.
    
    Args:
        image: Input image in BGR or grayscale.
        blur_threshold: Threshold below which image is deemed blurry.
        
    Returns:
        Dictionary with blur_score, is_blurry flag, width, height, and channels.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Compute the Laplacian variance (focus metric)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    height, width = gray.shape[:2]

    return {
        "blur_score": round(float(laplacian_var), 2),
        "is_blurry": bool(laplacian_var < blur_threshold),
        "width": int(width),
        "height": int(height),
        "is_too_small": bool(width < 300 or height < 200)
    }


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Converts a BGR image to grayscale."""
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_image(image: np.ndarray, target_width: int = 1800) -> np.ndarray:
    """
    Resizes image while maintaining aspect ratio to improve OCR readability
    for low-resolution scans.
    """
    height, width = image.shape[:2]
    if width >= target_width:
        return image
    
    scale = target_width / float(width)
    new_height = int(height * scale)
    return cv2.resize(image, (target_width, new_height), interpolation=cv2.INTER_CUBIC)


def enhance_contrast(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """
    Applies gentle CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to enhance text contrast against backgrounds without wiping out text.
    """
    gray = to_grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray)


def reduce_glare_and_background(image: np.ndarray) -> np.ndarray:
    """
    Soft illumination normalization using large kernel background estimation
    to prevent text erasure on colored cards (e.g. blue PAN cards).
    """
    gray = to_grayscale(image)
    # Use very large kernel so letters are never treated as background
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (81, 81))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    background = cv2.GaussianBlur(background, (51, 51), 0)
    # Safe division avoiding zero division
    background = np.maximum(background, 1)
    normalized = cv2.divide(gray, background, scale=255)
    # Blend 70% normalized with 30% original for maximum stability
    blended = cv2.addWeighted(normalized, 0.7, gray, 0.3, 0)
    return blended


def remove_noise(image: np.ndarray, d: int = 5) -> np.ndarray:
    """Applies Bilateral filter to preserve text edges while removing background texture."""
    gray = to_grayscale(image)
    return cv2.bilateralFilter(gray, d=d, sigmaColor=35, sigmaSpace=35)


def apply_threshold(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    """
    Applies thresholding (Otsu or Adaptive Gaussian) to separate text from background.
    """
    gray = to_grayscale(image)
    if method == "adaptive":
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 9
        )
    else:  # Otsu's binarization
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh


def sharpen_text(image: np.ndarray) -> np.ndarray:
    """Applies unsharp masking to sharpen text characters on low-contrast cards."""
    gray = to_grayscale(image)
    gaussian = cv2.GaussianBlur(gray, (0, 0), 1.5)
    unsharp = cv2.addWeighted(gray, 1.4, gaussian, -0.4, 0)
    return unsharp


def preprocess_id_card(
    image: np.ndarray,
    enable_resize: bool = True,
    enable_clahe: bool = True,
    enable_denoise: bool = False,
    enable_glare_reduction: bool = False,
    enable_sharpen: bool = True,
    enable_threshold: bool = False,
    threshold_method: str = "otsu"
) -> np.ndarray:
    """
    Complete modular preprocessing pipeline for Indian ID Cards.
    Optimized for RapidOCR deep learning DBNet model.
    """
    processed = image.copy()

    # Step 1: Resize if too small (maintains sharp text resolution)
    if enable_resize:
        processed = resize_image(processed, target_width=1800)

    # Step 2: Grayscale
    processed = to_grayscale(processed)

    # Step 3: Contrast Enhancement (CLAHE)
    if enable_clahe:
        processed = enhance_contrast(processed, clip_limit=2.0)

    # Step 4: Unsharp Mask Sharpening
    if enable_sharpen:
        processed = sharpen_text(processed)

    # Step 5: Optional gentle Glare reduction
    if enable_glare_reduction:
        processed = reduce_glare_and_background(processed)

    # Step 6: Noise smoothing
    if enable_denoise:
        processed = remove_noise(processed)

    # Step 7: Optional Binarization
    if enable_threshold:
        processed = apply_threshold(processed, method=threshold_method)

    return processed


_yolo_face_model = None

def get_yolo_face_model():
    """Lazily loads and caches the YOLO Face Detection model."""
    global _yolo_face_model
    if _yolo_face_model is not None:
        return _yolo_face_model
    try:
        from ultralytics import YOLO
        model_path = os.path.join(os.path.dirname(__file__), "yolov8n-face.pt")
        if not os.path.exists(model_path):
            model_path = "yolov8n-face.pt"
        if os.path.exists(model_path):
            _yolo_face_model = YOLO(model_path)
            return _yolo_face_model
    except Exception:
        pass
    return None


def extract_portrait_photo(image: np.ndarray, doc_type_hint: Optional[str] = None) -> Optional[str]:
    """
    Detects and cleanly extracts ONLY the applicant's person portrait (headshot) using YOLO Face Detection.
    - If doc_type is a back side (aadhaar_back, pan_back, etc.), returns None immediately.
    - Uses YOLO Face Detection to dynamically locate human faces anywhere on the document (no fixed coordinates).
    - Automatically ignores QR codes, EMV smart chips, and text blocks.
    - Adds optimal padding for hair, forehead, and collar.
    - Falls back to dual-zone skin contour analysis if needed.
    - Returns base64 data URI of the cropped headshot, or None if no valid face is found.
    """
    if image is None or image.size == 0:
        return None

    # Never extract portrait from document back sides
    if doc_type_hint and doc_type_hint.lower() in ["aadhaar_back", "pan_back", "driving_licence_back", "unsupported"]:
        return None

    try:
        h, w = image.shape[:2]
        if h < 50 or w < 50:
            return None

        # =========================================================================
        # 1. PRIMARY: High-Accuracy YOLO Face Detection (Zero Fixed Coordinates)
        # =========================================================================
        yolo = get_yolo_face_model()
        if yolo is not None:
            results = yolo(image, conf=0.25, verbose=False)
            boxes = results[0].boxes
            if len(boxes) > 0:
                best_box = None
                best_conf = -1.0
                for box in boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    fw = x2 - x1
                    fh = y2 - y1
                    # Validate realistic face aspect ratio and minimum size
                    if fw >= 20 and fh >= 20 and 0.55 <= (fh / float(fw)) <= 2.8:
                        if conf > best_conf:
                            best_conf = conf
                            best_box = (x1, y1, x2, y2, fw, fh)

                if best_box is not None:
                    x1, y1, x2, y2, fw, fh = best_box
                    # Add portrait padding for full headshot (hair, chin, collar)
                    pad_top = int(fh * 0.30)
                    pad_bot = int(fh * 0.25)
                    pad_x = int(fw * 0.20)

                    crop_top = max(0, y1 - pad_top)
                    crop_bot = min(h, y2 + pad_bot)
                    crop_left = max(0, x1 - pad_x)
                    crop_right = min(w, x2 + pad_x)

                    face_crop = image[crop_top:crop_bot, crop_left:crop_right]
                    if face_crop.shape[0] >= 30 and face_crop.shape[1] >= 30:
                        thumb = cv2.resize(face_crop, (150, 180), interpolation=cv2.INTER_AREA)
                        _, buffer = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
                        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        # =========================================================================
        # 2. FALLBACK: Dual-Zone Skin Segmentation & Morphological Face Detection
        # =========================================================================
        doc_hint = (doc_type_hint or "").lower()
        zone_left = (int(h * 0.12), int(h * 0.78), int(w * 0.05), int(w * 0.45), "left")
        zone_right = (int(h * 0.10), int(h * 0.78), int(w * 0.52), int(w * 0.98), "right")

        zones = [zone_left, zone_right] if doc_hint in ["pan", "pan_front"] else [zone_right, zone_left]
        best_crop = None
        best_score = 0.0

        for y1, y2, x1, x2, side in zones:
            sub = image[y1:y2, x1:x2]
            if sub.size == 0 or sub.shape[0] < 35 or sub.shape[1] < 35:
                continue

            # Smart Chip Rejection
            hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
            gold_mask = (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 38) & (hsv[:, :, 1] >= 100) & (hsv[:, :, 2] >= 90)
            gold_ratio = np.sum(gold_mask) / float(sub.shape[0] * sub.shape[1])
            if side == "left" and doc_hint in ["driving_licence", "dl"] and gold_ratio > 0.12:
                continue

            # Skin Segmentation
            ycrcb = cv2.cvtColor(sub, cv2.COLOR_BGR2YCrCb)
            skin_mask = (ycrcb[:, :, 1] >= 128) & (ycrcb[:, :, 1] <= 178) & (ycrcb[:, :, 2] >= 78) & (ycrcb[:, :, 2] <= 132)
            skin_ratio = np.sum(skin_mask) / float(sub.shape[0] * sub.shape[1])
            if skin_ratio < 0.04:
                continue

            mask_u8 = (skin_mask * 255).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            valid_faces = []
            for c in contours:
                area = cv2.contourArea(c)
                if area > 400:
                    fx, fy, fw, fh = cv2.boundingRect(c)
                    aspect = fh / float(fw) if fw > 0 else 0
                    if 0.60 <= aspect <= 2.6:
                        valid_faces.append((area, c, fx, fy, fw, fh))

            if not valid_faces:
                continue

            valid_faces.sort(key=lambda x: x[0], reverse=True)
            area, _, fx, fy, fw, fh = valid_faces[0]

            pad_top = int(fh * 0.22)
            pad_bot = int(fh * 0.18)
            pad_x = int(fw * 0.10)

            crop_top = max(0, fy - pad_top)
            crop_bot = min(sub.shape[0], fy + fh + pad_bot)
            crop_left = max(0, fx - pad_x)
            crop_right = min(sub.shape[1], fx + fw + pad_x)

            candidate_crop = sub[crop_top:crop_bot, crop_left:crop_right]
            score = area * skin_ratio

            if score > best_score:
                best_score = score
                best_crop = candidate_crop

        if best_crop is None:
            return None

        thumb = cv2.resize(best_crop, (150, 180), interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
    except Exception:
        return None


def preprocess_deep_multi_pass(image: np.ndarray) -> np.ndarray:
    """
    High-Accuracy Deep Multi-Pass enhancement for tough, skewed, or blurry retry scans.
    Applies multi-scale CLAHE, bilateral smoothing, and dynamic unsharp masking.
    """
    processed = resize_image(image.copy(), target_width=2000)
    gray = to_grayscale(processed)
    
    # Pass 1: Glare flattening
    glare_free = reduce_glare_and_background(gray)
    
    # Pass 2: Dynamic CLAHE
    clahe_fine = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6))
    enhanced = clahe_fine.apply(glare_free)
    
    # Pass 3: Edge-preserving bilateral filter
    denoised = cv2.bilateralFilter(enhanced, d=7, sigmaColor=75, sigmaSpace=75)
    
    # Pass 4: Unsharp masking
    gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.5)
    sharpened = cv2.addWeighted(denoised, 1.8, gaussian, -0.8, 0)
    
    return sharpened
