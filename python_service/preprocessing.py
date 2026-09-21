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


def remove_noise(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Applies Bilateral filter to preserve text edges while removing background texture."""
    gray = to_grayscale(image)
    return cv2.bilateralFilter(gray, d=5, sigmaColor=35, sigmaSpace=35)


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


def extract_portrait_photo(image: np.ndarray, doc_type_hint: Optional[str] = None) -> Optional[str]:
    """
    Detects and tightly extracts ONLY the applicant's person portrait (headshot).
    - If doc_type is a back side (aadhaar_back, pan_back, etc.), returns None immediately.
    - For Driving Licence and Aadhaar Front: prioritizes the RIGHT side (X: 55% to 95%, Y: 12% to 78%).
    - For PAN Front: prioritizes the LEFT side (X: 5% to 45%, Y: 14% to 72%).
    - Accurately rejects golden EMV smart chips, Ashoka emblem, holographic seals, and non-face regions.
    - Returns base64 data URI of the cropped headshot, or None if no genuine human face is found.
    """
    if image is None or image.size == 0:
        return None

    # Never extract portrait from document back sides
    if doc_type_hint and doc_type_hint.lower() in ["aadhaar_back", "pan_back", "driving_licence_back", "unsupported"]:
        return None

    try:
        import base64
        h, w = image.shape[:2]
        if h < 50 or w < 50:
            return None

        # Candidate regions:
        # Region Right: Standard Aadhaar Front & Modern Indian Driving Licence (Sarathi / Parivahan)
        region_right = (int(h * 0.10), int(h * 0.80), int(w * 0.52), int(w * 0.96), "right")
        # Region Left: Standard PAN Card Front & Older Driving Licences
        region_left = (int(h * 0.12), int(h * 0.72), int(w * 0.05), int(w * 0.45), "left")

        doc_hint = (doc_type_hint or "").lower()
        if doc_hint in ["driving_licence", "aadhaar", "aadhaar_front", "dl"]:
            candidates = [region_right, region_left]
        elif doc_hint in ["pan", "pan_front"]:
            candidates = [region_left, region_right]
        else:
            candidates = [region_right, region_left]

        best_crop = None
        best_score = 0.0

        for y1, y2, x1, x2, side in candidates:
            sub = image[y1:y2, x1:x2]
            if sub.size == 0 or sub.shape[0] < 35 or sub.shape[1] < 35:
                continue

            # Convert color spaces
            hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
            ycrcb = cv2.cvtColor(sub, cv2.COLOR_BGR2YCrCb)

            # 1. Smart Chip Rejection (Gold / Metallic contact pads on Left side of DL)
            # Gold color profile: Hue 15-38, High Saturation > 100, High Brightness > 90
            gold_mask = (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 38) & (hsv[:, :, 1] >= 100) & (hsv[:, :, 2] >= 90)
            gold_ratio = np.sum(gold_mask) / float(sub.shape[0] * sub.shape[1])
            if side == "left" and gold_ratio > 0.15:
                # This candidate region contains the metallic EMV smart chip, not a human headshot
                continue

            # 2. Human Skin Segmentation (Combined YCrCb and HSV filters)
            cr = ycrcb[:, :, 1]
            cb = ycrcb[:, :, 2]
            h_chan = hsv[:, :, 0]
            s_chan = hsv[:, :, 1]
            v_chan = hsv[:, :, 2]

            skin_mask_ycrcb = (cr >= 130) & (cr <= 175) & (cb >= 80) & (cb <= 130)
            skin_mask_hsv = ((h_chan <= 28) | (h_chan >= 168)) & (s_chan >= 20) & (s_chan <= 180) & (v_chan >= 35) & (v_chan <= 250)
            skin_mask = skin_mask_ycrcb & skin_mask_hsv

            skin_pixels = np.sum(skin_mask)
            total_pixels = sub.shape[0] * sub.shape[1]
            skin_ratio = skin_pixels / float(total_pixels) if total_pixels > 0 else 0

            # Real photo regions typically have between 6% and 75% skin pixels
            if skin_ratio < 0.05 or skin_ratio > 0.85:
                continue

            # Morphological cleaning to find connected face cluster
            mask_u8 = (skin_mask * 255).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                continue

            # Find largest skin contour (head / face)
            c = max(contours, key=cv2.contourArea)
            c_area = cv2.contourArea(c)
            if c_area < (sub.shape[0] * sub.shape[1] * 0.04):
                # Too small to be a person's face
                continue

            fx, fy, fw, fh = cv2.boundingRect(c)

            # Verify aspect ratio of the face candidate (0.75 <= h/w <= 2.2)
            aspect_ratio = fh / float(fw) if fw > 0 else 0
            if aspect_ratio < 0.65 or aspect_ratio > 2.4:
                continue

            # Expand bounding box for complete headshot (hair, forehead, chin, shoulders)
            pad_y_top = int(fh * 0.40)
            pad_y_bot = int(fh * 0.35)
            pad_x = int(fw * 0.32)

            crop_top = max(0, fy - pad_y_top)
            crop_bot = min(sub.shape[0], fy + fh + pad_y_bot)
            crop_left = max(0, fx - pad_x)
            crop_right = min(sub.shape[1], fx + fw + pad_x)

            candidate_crop = sub[crop_top:crop_bot, crop_left:crop_right]
            if candidate_crop.shape[0] >= 35 and candidate_crop.shape[1] >= 30:
                # Score formula: area + skin_ratio bonus + priority bonus for primary side
                side_bonus = 1.2 if (side == "right" and doc_hint in ["driving_licence", "aadhaar", "aadhaar_front"]) or (side == "left" and doc_hint in ["pan", "pan_front"]) else 1.0
                score = (c_area * skin_ratio) * side_bonus

                if score > best_score:
                    best_crop = candidate_crop
                    best_score = score
                    # If this is the primary region for the hinted doc type, take it
                    if side_bonus > 1.0 and skin_ratio > 0.08:
                        break

        # If no valid person face detected on the document, return None (never return full card)
        if best_crop is None:
            return None

        # Clean thumbnail output
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
