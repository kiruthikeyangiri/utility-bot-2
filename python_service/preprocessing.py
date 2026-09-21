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
    Detects and cleanly extracts ONLY the applicant's person portrait (headshot).
    - If doc_type is a back side (aadhaar_back, pan_back, etc.), returns None immediately.
    - For Driving Licence (DL): Extracts the RIGHT photo box (Y: 16%-49%, X: 63%-80%) avoiding the left smart chip.
    - For Aadhaar Front: Extracts the RIGHT photo box (Y: 15%-66%, X: 60%-92%).
    - For PAN Front: Extracts the LEFT photo box (Y: 16%-66%, X: 6%-40%).
    - Returns base64 data URI of the cropped headshot, or None if no valid photo is found.
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

        doc_hint = (doc_type_hint or "").lower()

        # 1. Target candidate bounding region based on document specification
        if doc_hint in ["driving_licence", "dl"]:
            # Driving Licence standard: Photo is strictly on the RIGHT side
            sub = image[int(h * 0.165):int(h * 0.49), int(w * 0.635):int(w * 0.795)]
        elif doc_hint in ["aadhaar", "aadhaar_front"]:
            # Aadhaar Front standard: Photo is strictly on the RIGHT side
            sub = image[int(h * 0.15):int(h * 0.66), int(w * 0.60):int(w * 0.92)]
        elif doc_hint in ["pan", "pan_front"]:
            # PAN Card standard: Photo is strictly on the LEFT side
            sub = image[int(h * 0.16):int(h * 0.66), int(w * 0.06):int(w * 0.40)]
        else:
            # General fallback: check right region first (DL / Aadhaar)
            sub = image[int(h * 0.16):int(h * 0.50), int(w * 0.62):int(w * 0.82)]

        if sub.size == 0 or sub.shape[0] < 30 or sub.shape[1] < 30:
            return None

        # 2. Check for skin tones to confirm a person's photo is present
        ycrcb = cv2.cvtColor(sub, cv2.COLOR_BGR2YCrCb)
        cr = ycrcb[:, :, 1]
        cb = ycrcb[:, :, 2]
        skin_mask = (cr >= 125) & (cr <= 180) & (cb >= 75) & (cb <= 135)
        skin_ratio = np.sum(skin_mask) / float(sub.shape[0] * sub.shape[1])

        # If low skin ratio, verify image variance (e.g. grayscale / dark photo)
        if skin_ratio < 0.03:
            gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            if np.std(gray) < 16:
                return None

        # 3. Clean and return 150x180 thumbnail
        thumb = cv2.resize(sub, (150, 180), interpolation=cv2.INTER_AREA)
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
