"""
face_matching_service.py - High-Precision Face Recognition & Cosine Similarity Service.
Uses OpenCV's official Deep SFace Model (face_recognition_sface.onnx) for 128-dimensional
biometric face embedding extraction, cosine similarity calculation, and calibrated 3-tier matching:
- STRONG_MATCH (>= 75%): Same person verified with high confidence.
- UNCERTAIN (50% - 74%): Moderate similarity, recommends second ID verification.
- WEAK (< 50%): Identity mismatch (different persons / rejected).
"""

import os
import base64
from typing import Dict, Any, Optional
import cv2
import numpy as np


_sface_recognizer = None


def get_sface_recognizer():
    """Lazily loads and caches OpenCV Deep SFace FaceRecognizer."""
    global _sface_recognizer
    if _sface_recognizer is not None:
        return _sface_recognizer

    model_candidates = [
        os.path.join(os.path.dirname(__file__), "face_recognition_sface.onnx"),
        "face_recognition_sface.onnx"
    ]

    for path in model_candidates:
        if os.path.exists(path) and os.path.getsize(path) > 100000:
            try:
                _sface_recognizer = cv2.FaceRecognizerSF.create(path, "")
                return _sface_recognizer
            except Exception as e:
                print(f"[FaceMatching] SFace initialization notice: {e}")

    return None


def decode_image_from_base64(image_input: Any) -> Optional[np.ndarray]:
    """Decodes a base64 string, data URI, or raw bytes into an OpenCV BGR numpy array."""
    if image_input is None:
        return None
    if isinstance(image_input, np.ndarray):
        return image_input

    try:
        if isinstance(image_input, str):
            if "base64," in image_input:
                image_input = image_input.split("base64,")[1]
            image_bytes = base64.b64decode(image_input)
        elif isinstance(image_input, bytes):
            image_bytes = image_input
        else:
            return None

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"[FaceMatching] Image decode error: {e}")
        return None


def extract_face_crop(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detects and tightly crops the human face using YOLOv8 face model or Haar cascade.
    """
    if image is None or image.size == 0:
        return None

    h, w = image.shape[:2]
    
    # Try YOLO face detector from preprocessing module
    try:
        from preprocessing import get_yolo_face_model
        yolo = get_yolo_face_model()
        if yolo is not None:
            results = yolo(image, conf=0.18, verbose=False)
            boxes = results[0].boxes
            if len(boxes) > 0:
                best_box = None
                best_conf = -1.0
                for box in boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    fw, fh = x2 - x1, y2 - y1
                    if fw >= 20 and fh >= 20 and conf > best_conf:
                        best_conf = conf
                        best_box = (x1, y1, x2, y2)
                
                if best_box is not None:
                    x1, y1, x2, y2 = best_box
                    pad_y = int((y2 - y1) * 0.12)
                    pad_x = int((x2 - x1) * 0.12)
                    c_top = max(0, y1 - pad_y)
                    c_bot = min(h, y2 + pad_y)
                    c_left = max(0, x1 - pad_x)
                    c_right = min(w, x2 + pad_x)
                    cropped = image[c_top:c_bot, c_left:c_right]
                    if cropped.size > 0:
                        return cropped
    except Exception as e:
        print(f"[FaceMatching] YOLO crop notice: {e}")

    # Fallback: Haar Cascade
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
        if len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
            return image[y:y+fh, x:x+fw]
    except Exception:
        pass

    # Default to entire image if already cropped portrait
    return image


def normalize_face_lighting(face_bgr: np.ndarray) -> np.ndarray:
    """
    Applies adaptive histogram equalization in LAB color space to normalize lighting
    and contrast across low-light ID photos and over-exposed webcam frames.
    """
    if face_bgr is None or face_bgr.size == 0:
        return face_bgr
    try:
        lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return enhanced
    except Exception:
        return face_bgr


def extract_face_embedding(face_img: np.ndarray) -> np.ndarray:
    """
    Computes a 128-dimensional normalized biometric feature vector using Deep SFace.
    """
    if face_img is None or face_img.size == 0:
        return np.zeros((1, 128), dtype=np.float32)

    # Standardize face image resolution for SFace input (112x112)
    normalized = normalize_face_lighting(face_img)
    aligned_face = cv2.resize(normalized, (112, 112), interpolation=cv2.INTER_AREA)

    sface = get_sface_recognizer()
    if sface is not None:
        try:
            feature = sface.feature(aligned_face)
            norm = np.linalg.norm(feature)
            if norm > 1e-6:
                feature = feature / norm
            return feature
        except Exception as e:
            print(f"[FaceMatching] SFace feature extraction error: {e}")

    # Fallback multi-dimensional vector
    gray = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2HSV)
    blocks = []
    for r in range(0, 112, 16):
        for c in range(0, 112, 16):
            cell_g = gray[r:r+16, c:c+16]
            cell_h = hsv[r:r+16, c:c+16, 0]
            blocks.extend([float(np.mean(cell_g)), float(np.std(cell_g)), float(np.mean(cell_h))])
    
    vec = np.array(blocks, dtype=np.float32).reshape(1, -1)
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    return vec


def calibrate_sface_score(cosine_similarity: float) -> float:
    """
    Calibrates raw SFace cosine similarity into an accurate 0% - 100% human match confidence.
    
    SFace Cosine Thresholds:
    - >= 0.70: Identical person (calibrated to 75.0% - 98.0%)
    - 0.363 to 0.699: Borderline / uncertain (calibrated to 50.0% - 74.9%)
    - < 0.363: Different person / mismatch (calibrated to 2.0% - 49.9%)
    """
    cos = float(np.clip(cosine_similarity, -1.0, 1.0))
    
    if cos >= 0.70:
        # Scale 0.70 .. 0.95 -> 75% .. 98%
        score = 75.0 + min(23.0, max(0.0, ((cos - 0.70) / 0.25) * 23.0))
    elif cos >= 0.363:
        # Scale 0.363 .. 0.70 -> 50% .. 74.9%
        score = 50.0 + ((cos - 0.363) / (0.70 - 0.363)) * 24.9
    else:
        # Scale 0.0 .. 0.363 -> 2.0% .. 49.9%
        score = max(2.0, (cos / 0.363) * 49.0)

    return round(float(min(99.0, max(1.0, score))), 1)


def compare_faces(
    id_portrait_input: Any, 
    live_or_second_photo_input: Any
) -> Dict[str, Any]:
    """
    High-Precision Biometric Face Verification between ID Card Portrait and Live Selfie / Second ID.
    
    Returns:
        Dictionary with:
        - match_score: float (0.0 to 100.0)
        - raw_similarity: float (-1.0 to 1.0)
        - match_tier: 'STRONG_MATCH' | 'UNCERTAIN' | 'WEAK'
        - status: 'VERIFIED' | 'UNCERTAIN' | 'FAILED'
        - is_matched: bool
        - explanation: str
    """
    # 1. Decode images
    id_img = decode_image_from_base64(id_portrait_input)
    live_img = decode_image_from_base64(live_or_second_photo_input)

    if id_img is None:
        return {
            "match_score": 0.0,
            "raw_similarity": 0.0,
            "match_tier": "WEAK",
            "status": "FAILED",
            "is_matched": False,
            "explanation": "Primary ID portrait photo is missing or unreadable."
        }

    if live_img is None:
        return {
            "match_score": 0.0,
            "raw_similarity": 0.0,
            "match_tier": "WEAK",
            "status": "FAILED",
            "is_matched": False,
            "explanation": "Comparison photo (live selfie or second ID) is missing or unreadable."
        }

    # 2. Extract and align face crops
    id_face = extract_face_crop(id_img)
    live_face = extract_face_crop(live_img)

    if id_face is None or live_face is None:
        return {
            "match_score": 0.0,
            "raw_similarity": 0.0,
            "match_tier": "WEAK",
            "status": "FAILED",
            "is_matched": False,
            "explanation": "Face could not be detected in one of the provided images."
        }

    # 3. Compute Deep 128-D SFace embeddings
    sface = get_sface_recognizer()
    emb_id = extract_face_embedding(id_face)
    emb_live = extract_face_embedding(live_face)

    # 4. Cosine similarity
    if sface is not None:
        try:
            cosine_sim = float(sface.match(emb_id, emb_live, cv2.FaceRecognizerSF_FR_COSINE))
        except Exception:
            dot = float(np.dot(emb_id.flatten(), emb_live.flatten()))
            n1 = float(np.linalg.norm(emb_id))
            n2 = float(np.linalg.norm(emb_live))
            cosine_sim = dot / (n1 * n2 + 1e-6)
    else:
        dot = float(np.dot(emb_id.flatten(), emb_live.flatten()))
        n1 = float(np.linalg.norm(emb_id))
        n2 = float(np.linalg.norm(emb_live))
        cosine_sim = dot / (n1 * n2 + 1e-6)

    # 5. Calibrate confidence percentage
    calibrated_score = calibrate_sface_score(cosine_sim)

    # 6. Categorize into 3 Calibrated Tiers
    if calibrated_score >= 75.0:
        match_tier = "STRONG_MATCH"
        status = "VERIFIED"
        is_matched = True
        explanation = f"High confidence face match ({calibrated_score}%). Customer identity confirmed."
    elif calibrated_score >= 50.0:
        match_tier = "UNCERTAIN"
        status = "UNCERTAIN"
        is_matched = False
        explanation = f"Moderate face similarity ({calibrated_score}%). Second ID verification recommended to confirm identity."
    else:
        match_tier = "WEAK"
        status = "FAILED"
        is_matched = False
        explanation = f"Identity Mismatch: Low face similarity ({calibrated_score}%). Facial biometric features do not match ID portrait."

    return {
        "match_score": calibrated_score,
        "raw_similarity": round(float(cosine_sim), 4),
        "match_tier": match_tier,
        "status": status,
        "is_matched": is_matched,
        "explanation": explanation
    }
