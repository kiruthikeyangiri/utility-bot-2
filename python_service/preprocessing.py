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
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to enhance text contrast against backgrounds with gradients or watermarks.
    """
    gray = to_grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray)


def reduce_glare_and_background(image: np.ndarray) -> np.ndarray:
    """
    Reduces uneven illumination and glare from laminated ID cards
    using morphological opening background subtraction.
    """
    gray = to_grayscale(image)
    # Estimate background illumination with large morphological kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    # Divide original by background to flatten illumination
    normalized = cv2.divide(gray, background, scale=255)
    return normalized


def remove_noise(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Applies Bilateral filter to preserve text edges while removing background texture."""
    gray = to_grayscale(image)
    return cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)


def apply_threshold(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    """
    Applies thresholding (Otsu or Adaptive Gaussian) to separate text from background.
    """
    gray = to_grayscale(image)
    if method == "adaptive":
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19, 9
        )
    else:  # Otsu's binarization
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh


def sharpen_text(image: np.ndarray) -> np.ndarray:
    """Applies unsharp masking to sharpen text characters on low-contrast cards."""
    gray = to_grayscale(image)
    gaussian = cv2.GaussianBlur(gray, (0, 0), 2.0)
    unsharp = cv2.addWeighted(gray, 1.6, gaussian, -0.6, 0)
    return unsharp


def preprocess_id_card(
    image: np.ndarray,
    enable_resize: bool = True,
    enable_clahe: bool = True,
    enable_denoise: bool = True,
    enable_glare_reduction: bool = True,
    enable_sharpen: bool = True,
    enable_threshold: bool = False,
    threshold_method: str = "otsu"
) -> np.ndarray:
    """
    Complete modular preprocessing pipeline for Indian ID Cards.
    Optimized for laminated cards with background watermarks/holograms.
    """
    processed = image.copy()

    # Step 1: Resize if too small
    if enable_resize:
        processed = resize_image(processed, target_width=1800)

    # Step 2: Convert to Grayscale
    processed = to_grayscale(processed)

    # Step 3: Illumination & Glare Flattening
    if enable_glare_reduction:
        processed = reduce_glare_and_background(processed)

    # Step 4: Contrast Enhancement (CLAHE)
    if enable_clahe:
        processed = enhance_contrast(processed, clip_limit=2.5)

    # Step 5: Unsharp Mask Sharpening
    if enable_sharpen:
        processed = sharpen_text(processed)

    # Step 6: Noise & Texture Smoothing (Bilateral Filter)
    if enable_denoise:
        processed = remove_noise(processed)

    # Step 7: Optional Binarization / Thresholding
    if enable_threshold:
        processed = apply_threshold(processed, method=threshold_method)

    return processed
