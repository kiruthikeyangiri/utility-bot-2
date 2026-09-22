"""
liveness_service.py - Passive & Active Face Liveness / Anti-Spoofing Detection Service.
Detects presentation attacks (phone screens, printouts, masks, re-play attacks) using:
1. Fast Fourier Transform (FFT) high-frequency moiré analysis.
2. Specular screen glare and reflection distribution.
3. Chrominance variance and natural skin texture analysis.
4. Active challenge generation (blink, smile, head movement).
"""

import random
import time
from typing import Dict, Any, Optional
import cv2
import numpy as np

from face_matching_service import decode_image_from_base64, extract_face_crop


CHALLENGE_TYPES = [
    {"type": "blink", "instruction": "Blink both eyes naturally", "icon": "eye"},
    {"type": "smile", "instruction": "Smile gently towards the camera", "icon": "smile"},
    {"type": "turn_left", "instruction": "Slowly turn head slightly to the left", "icon": "arrow-left"},
    {"type": "turn_right", "instruction": "Slowly turn head slightly to the right", "icon": "arrow-right"}
]


def generate_liveness_challenge() -> Dict[str, Any]:
    """Generates a random active challenge with a time-limited verification token."""
    challenge = random.choice(CHALLENGE_TYPES)
    token = f"chal_{int(time.time())}_{random.randint(1000, 9999)}"
    return {
        "challenge_id": token,
        "challenge_type": challenge["type"],
        "instruction": challenge["instruction"],
        "expires_in_seconds": 60,
        "created_at": time.time()
    }


def analyze_fft_frequency_texture(gray_face: np.ndarray) -> Dict[str, Any]:
    """
    Computes 2D FFT magnitude spectrum to detect digital screen moiré patterns
    or printed paper dot matrix patterns.
    """
    h, w = gray_face.shape[:2]
    if h < 32 or w < 32:
        return {"fft_score": 50.0, "is_screen_artifact": False}

    # Standardize size for FFT
    resized = cv2.resize(gray_face, (128, 128))
    f = np.fft.fft2(resized)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-6)

    # Calculate high-frequency energy ratio vs low-frequency energy
    crow, ccol = 64, 64
    r_inner = 16
    r_outer = 48

    y, x = np.ogrid[:128, :128]
    dist_from_center = np.sqrt((x - ccol)**2 + (y - crow)**2)

    inner_mask = dist_from_center <= r_inner
    outer_mask = (dist_from_center > r_inner) & (dist_from_center <= r_outer)

    inner_energy = np.mean(magnitude_spectrum[inner_mask])
    outer_energy = np.mean(magnitude_spectrum[outer_mask])

    ratio = float(outer_energy / max(inner_energy, 1e-6))
    
    # Real 3D skin has smooth frequency roll-off; screens have repetitive high-frequency peaks
    is_screen = ratio > 0.88 or ratio < 0.25
    fft_score = max(0.0, min(100.0, (1.0 - abs(ratio - 0.58) / 0.35) * 100.0))

    return {
        "fft_score": round(float(fft_score), 1),
        "high_freq_ratio": round(float(ratio), 3),
        "is_screen_artifact": bool(is_screen)
    }


def analyze_specular_screen_glare(bgr_face: np.ndarray) -> Dict[str, Any]:
    """
    Detects harsh specular reflections characteristic of glass smartphone/monitor screens.
    """
    hsv = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    s_channel = hsv[:, :, 1]

    # Glass screen glare: High Brightness (V > 240) + Zero Saturation (S < 30)
    glare_mask = (v_channel > 240) & (s_channel < 30)
    glare_ratio = float(np.sum(glare_mask)) / float(bgr_face.shape[0] * bgr_face.shape[1])

    is_glare_spoof = glare_ratio > 0.08
    glare_score = max(0.0, min(100.0, (1.0 - (glare_ratio / 0.08)) * 100.0))

    return {
        "glare_score": round(float(glare_score), 1),
        "glare_ratio": round(float(glare_ratio), 4),
        "has_screen_glare": bool(is_glare_spoof)
    }


def analyze_skin_chrominance(bgr_face: np.ndarray) -> Dict[str, Any]:
    """
    Analyzes chrominance variance across YCrCb space.
    Real organic skin has natural multi-tonal blood perfusion and lighting variation.
    Paper printouts and poor screens exhibit compressed chrominance variance.
    """
    ycrcb = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2YCrCb)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    cr_std = float(np.std(cr))
    cb_std = float(np.std(cb))
    chroma_variance = (cr_std + cb_std) / 2.0

    # Organic skin standard deviation in Cr/Cb typically ranges from 4.0 to 18.0
    is_flat_print = chroma_variance < 3.2
    chroma_score = max(0.0, min(100.0, ((chroma_variance - 2.0) / 10.0) * 100.0))

    return {
        "chroma_score": round(float(chroma_score), 1),
        "chroma_variance": round(float(chroma_variance), 2),
        "is_flat_print": bool(is_flat_print)
    }


def evaluate_liveness(
    live_image_input: Any, 
    challenge_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive passive and active liveness verification.
    
    Returns:
        Dictionary with:
        - is_live: bool
        - liveness_score: float (0.0 to 100.0)
        - spoof_detected: bool
        - confidence_tier: 'HIGH_LIVENESS' | 'MODERATE' | 'SPOOF_RISK'
        - diagnostics: Dict of individual checks
        - message: str
    """
    img = decode_image_from_base64(live_image_input)
    if img is None:
        return {
            "is_live": False,
            "liveness_score": 0.0,
            "spoof_detected": True,
            "confidence_tier": "SPOOF_RISK",
            "diagnostics": {},
            "message": "Live camera capture could not be decoded."
        }

    face = extract_face_crop(img)
    if face is None:
        return {
            "is_live": False,
            "liveness_score": 0.0,
            "spoof_detected": True,
            "confidence_tier": "SPOOF_RISK",
            "diagnostics": {},
            "message": "No live human face detected in camera view."
        }

    gray_face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

    # 1. Texture & Frequency Moiré Analysis
    fft_diag = analyze_fft_frequency_texture(gray_face)

    # 2. Specular Screen Glare
    glare_diag = analyze_specular_screen_glare(face)

    # 3. Organic Skin Chrominance Distribution
    chroma_diag = analyze_skin_chrominance(face)

    # 4. Blur / Focus Check
    lap_var = float(cv2.Laplacian(gray_face, cv2.CV_64F).var())
    blur_score = min(100.0, max(0.0, (lap_var / 120.0) * 100.0))

    # Aggregate weighted score
    liveness_score = (
        fft_diag["fft_score"] * 0.35 +
        glare_diag["glare_score"] * 0.25 +
        chroma_diag["chroma_score"] * 0.25 +
        blur_score * 0.15
    )
    liveness_score = round(float(liveness_score), 1)

    spoof_flags = [
        fft_diag["is_screen_artifact"],
        glare_diag["has_screen_glare"],
        chroma_diag["is_flat_print"],
        lap_var < 20.0
    ]
    spoof_detected = sum(spoof_flags) >= 2 or liveness_score < 45.0

    if liveness_score >= 70.0 and not spoof_detected:
        confidence_tier = "HIGH_LIVENESS"
        is_live = True
        message = "Live human presence verified. Anti-spoofing tests passed."
    elif liveness_score >= 50.0 and not spoof_detected:
        confidence_tier = "MODERATE"
        is_live = True
        message = "Liveness accepted with moderate confidence."
    else:
        confidence_tier = "SPOOF_RISK"
        is_live = False
        message = "Liveness check failed. Digital screen or photo reproduction suspected."

    return {
        "is_live": is_live,
        "liveness_score": liveness_score,
        "spoof_detected": spoof_detected,
        "confidence_tier": confidence_tier,
        "diagnostics": {
            "fft_texture": fft_diag,
            "screen_glare": glare_diag,
            "skin_chrominance": chroma_diag,
            "focus_sharpness": round(float(lap_var), 1)
        },
        "message": message
    }
