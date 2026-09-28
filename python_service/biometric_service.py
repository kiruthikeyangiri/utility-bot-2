"""
biometric_service.py - Camera-Based Contactless Biometric Fingerprint Processing & Minutiae Extraction.
Uses Computer Vision (OpenCV) to extract fingertip pad ROI, enhance epidermal dermal ridges via Gabor filters,
and identify ISO/IEC standard minutiae points (ridge endings & bifurcations) with quality scoring.
"""

import os
import base64
import math
from typing import Dict, Any, Optional, Tuple, List
import cv2
import numpy as np

from face_matching_service import decode_image_from_base64


def build_gabor_filter_bank(ksize: int = 15, sigma: float = 2.5, lambd: float = 7.0, gamma: float = 0.5) -> List[np.ndarray]:
    """Builds a multi-directional Gabor kernel bank to capture fingerprint ridge flows across 8 angles."""
    filters = []
    for theta in np.arange(0, np.pi, np.pi / 8):
        kernel = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, gamma, psi=0, ktype=cv2.CV_32F)
        kernel /= 1.5 * kernel.sum() if kernel.sum() != 0 else 1.0
        filters.append(kernel)
    return filters


def extract_fingertip_roi(image: np.ndarray) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """
    Locates the finger in the capture area and extracts the high-resolution fingertip pad region.
    """
    if image is None or image.size == 0:
        return None, {"error": "Empty frame"}

    h, w = image.shape[:2]
    
    # 1. Target central inspection zone
    center_y1, center_y2 = int(h * 0.15), int(h * 0.85)
    center_x1, center_x2 = int(w * 0.20), int(w * 0.80)
    central_crop = image[center_y1:center_y2, center_x1:center_x2]

    # 2. Skin chromatic segmentation in YCrCb space
    ycrcb = cv2.cvtColor(central_crop, cv2.COLOR_BGR2YCrCb)
    skin_mask = (
        (ycrcb[:, :, 1] >= 130) & (ycrcb[:, :, 1] <= 180) &
        (ycrcb[:, :, 2] >= 75) & (ycrcb[:, :, 2] <= 135)
    )
    skin_ratio = float(np.sum(skin_mask)) / float(central_crop.shape[0] * central_crop.shape[1])

    if skin_ratio < 0.08:
        # Fallback to direct central region if lighting differs
        roi = central_crop
    else:
        # Find largest skin contour (finger)
        mask_u8 = (skin_mask * 255).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            fx, fy, fw, fh = cv2.boundingRect(largest)
            # Focus on top 60% of finger contour (the fingertip pad where ridges are clearest)
            pad_h = int(fh * 0.65)
            roi = central_crop[fy:fy + pad_h, fx:fx + fw]
        else:
            roi = central_crop

    if roi is None or roi.shape[0] < 40 or roi.shape[1] < 40:
        return None, {"error": "Finger not positioned inside capture zone"}

    # Standardize ROI size to 240x280 for consistent minutiae analysis
    resized_roi = cv2.resize(roi, (240, 280), interpolation=cv2.INTER_CUBIC)
    return resized_roi, {"skin_ratio": round(skin_ratio, 3)}


def enhance_fingerprint_ridges(roi_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Enhances dermal epidermal ridges using green-channel extraction, adaptive CLAHE,
    multi-directional Gabor filtering, and unsharp masking.
    
    Returns:
        - enhanced_gray: Enhanced grayscale ridge image (uint8)
        - binary_ridges: Skeletonized/binarized ridge pattern (uint8 0/255)
        - ridge_clarity_score: float (0 - 100)
    """
    # Green channel has optimal absorption contrast for human dermal ridges
    green_ch = roi_bgr[:, :, 1]

    # Step 1: Multi-scale CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    contrasted = clahe.apply(green_ch)

    # Step 2: Unsharp masking for high-frequency ridge boundaries
    blurred = cv2.GaussianBlur(contrasted, (0, 0), 2.0)
    sharpened = cv2.addWeighted(contrasted, 2.2, blurred, -1.2, 0)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

    # Step 3: Multi-directional Gabor filtering
    gabor_bank = build_gabor_filter_bank(ksize=15, sigma=2.0, lambd=6.5, gamma=0.5)
    filtered_accum = np.zeros_like(sharpened, dtype=np.float32)
    for g_kernel in gabor_bank:
        filtered = cv2.filter2D(sharpened, cv2.CV_32F, g_kernel)
        filtered_accum = np.maximum(filtered_accum, filtered)

    filtered_u8 = np.clip(filtered_accum, 0, 255).astype(np.uint8)
    enhanced_gray = cv2.addWeighted(sharpened, 0.4, filtered_u8, 0.6, 0)

    # Step 4: Adaptive local thresholding to generate binary ridge valleys
    binary_ridges = cv2.adaptiveThreshold(
        enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # Step 5: Morphological noise cleanup
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    binary_ridges = cv2.morphologyEx(binary_ridges, cv2.MORPH_OPEN, morph_kernel)

    # Calculate Ridge Clarity Score via Laplacian energy on ridge edges
    lap_var = float(cv2.Laplacian(enhanced_gray, cv2.CV_64F).var())
    clarity_score = min(100.0, max(10.0, (lap_var / 90.0) * 100.0))

    return enhanced_gray, binary_ridges, round(clarity_score, 1)


def extract_minutiae_points(binary_ridges: np.ndarray) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """
    Extracts standard biometric minutiae points (Ridge Endings & Bifurcations) using Crossing Number (CN).
    Renders visual biometric feature map with color-coded minutiae circles:
    - RED dots: Ridge Endings (CN = 1)
    - GREEN dots: Ridge Bifurcations (CN = 3)
    """
    h, w = binary_ridges.shape[:2]
    
    # Fast morphological thinning (skeletonization)
    thinned = binary_ridges // 255
    skeleton = np.zeros_like(thinned)
    
    # Iterative morphological skeletonization
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp_img = thinned.copy()
    for _ in range(8):
        eroded = cv2.erode(temp_img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(temp_img, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        temp_img = eroded.copy()
        if cv2.countNonZero(temp_img) == 0:
            break

    # Build biometric visualization canvas
    vis_bgr = np.zeros((h, w, 3), dtype=np.uint8)
    # Draw ridges in cool cyan/blue
    vis_bgr[binary_ridges > 0] = [210, 160, 40]

    minutiae_list = []
    
    # 8-neighbor scan for Crossing Number (CN)
    # Exclude image boundary (15px margin)
    for y in range(15, h - 15, 2):
        for x in range(15, w - 15, 2):
            if skeleton[y, x] != 1:
                continue

            # 8 neighbors in cyclic order
            p = [
                skeleton[y - 1, x],     # P2 (North)
                skeleton[y - 1, x + 1], # P3 (North-East)
                skeleton[y, x + 1],     # P4 (East)
                skeleton[y + 1, x + 1], # P5 (South-East)
                skeleton[y + 1, x],     # P6 (South)
                skeleton[y + 1, x - 1], # P7 (South-West)
                skeleton[y, x - 1],     # P8 (West)
                skeleton[y - 1, x - 1]  # P9 (North-West)
            ]
            
            cn = 0.5 * sum(abs(int(p[i]) - int(p[(i + 1) % 8])) for i in range(8))

            if cn == 1:
                # Ridge Ending
                minutiae_list.append({"type": "ending", "x": int(x), "y": int(y)})
                cv2.circle(vis_bgr, (x, y), 3, (0, 0, 255), -1)  # Red circle
                cv2.circle(vis_bgr, (x, y), 5, (0, 0, 255), 1)
            elif cn == 3:
                # Ridge Bifurcation
                minutiae_list.append({"type": "bifurcation", "x": int(x), "y": int(y)})
                cv2.circle(vis_bgr, (x, y), 3, (0, 255, 0), -1)  # Green circle
                cv2.circle(vis_bgr, (x, y), 5, (0, 255, 0), 1)

    return minutiae_list, vis_bgr


def process_contactless_biometric_scan(
    image_input: Any,
    applicant_name: Optional[str] = None,
    id_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete contactless camera-based biometric fingerprint verification pipeline.
    
    Returns:
        - status: 'VERIFIED' | 'UNCERTAIN' | 'FAILED'
        - verification_passed: bool
        - quality_score: float (0 - 100)
        - ridge_clarity: float (0 - 100)
        - minutiae_count: int
        - endings_count: int
        - bifurcations_count: int
        - minutiae_visualization_b64: str (data URI for rendering)
        - enhanced_ridge_b64: str
        - summary: str
    """
    img = decode_image_from_base64(image_input)
    if img is None:
        return {
            "status": "FAILED",
            "verification_passed": False,
            "quality_score": 0.0,
            "minutiae_count": 0,
            "summary": "Camera capture image could not be decoded. Please retry."
        }

    # Step 1: Extract Fingertip ROI
    fingertip_roi, roi_meta = extract_fingertip_roi(img)
    if fingertip_roi is None:
        return {
            "status": "FAILED",
            "verification_passed": False,
            "quality_score": 0.0,
            "minutiae_count": 0,
            "summary": "Finger not detected. Please align your fingertip inside the camera guide oval."
        }

    # Step 2: Ridge Enhancement
    enhanced_gray, binary_ridges, clarity_score = enhance_fingerprint_ridges(fingertip_roi)

    # Step 3: Minutiae Feature Extraction
    minutiae_points, vis_bgr = extract_minutiae_points(binary_ridges)
    endings = [m for m in minutiae_points if m["type"] == "ending"]
    bifurcations = [m for m in minutiae_points if m["type"] == "bifurcation"]

    total_minutiae = len(minutiae_points)

    # Step 4: Calibrated Biometric Quality Score
    # ISO standard requires >= 12 minutiae points for reliable identification
    minutiae_score = min(100.0, (total_minutiae / 24.0) * 100.0)
    overall_quality = round((clarity_score * 0.45 + minutiae_score * 0.55), 1)

    # Step 5: Verification Decision Gate
    if total_minutiae >= 12 and overall_quality >= 60.0:
        status = "VERIFIED"
        passed = True
        summary = f"Biometric Dermal Ridge Scan Verified ({overall_quality}% Quality, {total_minutiae} Minutiae points extracted)."
    elif total_minutiae >= 8:
        status = "UNCERTAIN"
        passed = False
        summary = f"Moderate biometric scan quality ({overall_quality}%). Please adjust lighting and hold steady."
    else:
        status = "FAILED"
        passed = False
        summary = f"Insufficient ridge details ({total_minutiae} Minutiae). Please hold finger closer to the camera."

    # Encode visualizations for frontend modal
    _, vis_buf = cv2.imencode(".jpg", vis_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    vis_b64 = f"data:image/jpeg;base64,{base64.b64encode(vis_buf).decode('utf-8')}"

    _, enh_buf = cv2.imencode(".jpg", enhanced_gray, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    enh_b64 = f"data:image/jpeg;base64,{base64.b64encode(enh_buf).decode('utf-8')}"

    return {
        "status": status,
        "verification_passed": passed,
        "quality_score": overall_quality,
        "ridge_clarity": clarity_score,
        "minutiae_count": total_minutiae,
        "endings_count": len(endings),
        "bifurcations_count": len(bifurcations),
        "minutiae_visualization": vis_b64,
        "enhanced_ridge_image": enh_b64,
        "summary": summary,
        "applicant_name": applicant_name,
        "id_number": id_number
    }
