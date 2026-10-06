"""
main.py - FastAPI Microservice for ID Card Information Extraction.
Exposes REST endpoints for image preprocessing, OCR, Decision Gate check,
Groq LLM extraction, Pydantic validation, and Human-in-the-Loop Confirmation Gateway.
"""

import io
import os
from contextlib import asynccontextmanager

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

from typing import Optional, Dict, Any, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from shipping_schemas import ShippingLabelResult, CodeItem
from shipping_extractor import extract_shipping_label_data, extract_shipping_info_llm
from code_reader import extract_codes


from schemas import (
    FinalExtractionResult, 
    UnsupportedDocumentData, 
    ConfirmationRequest,
    LiveFaceVerificationRequest,
    SecondIdVerificationRequest
)
from preprocessing import (
    assess_image_quality, 
    preprocess_id_card, 
    extract_portrait_photo, 
    preprocess_deep_multi_pass
)
from ocr_engine import extract_ocr_data, draw_bounding_boxes, check_tesseract_available, get_ocr_reader
from document_classifier import classify_document_heuristics
from llm_extractor import extract_document_info, get_available_models
from validation import validate_and_clean_extraction
from utils import pil_to_cv2, cv2_to_base64, logger
from face_matching_service import compare_faces
from liveness_service import evaluate_liveness, generate_liveness_challenge
from document_crosscheck_service import cross_verify_documents
from storage import (
    save_confirmed_verification, 
    get_history, 
    get_failed_history, 
    get_extraction_by_id, 
    delete_extraction_by_id, 
    get_storage_stats, 
    clean_storage
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm RapidOCR engine and YOLO model on startup."""
    try:
        logger.info("Initializing and pre-warming RapidOCR ONNX engine...")
        get_ocr_reader()
        logger.info("RapidOCR engine initialized successfully.")
    except Exception as e:
        logger.warning(f"RapidOCR warmup warning: {e}")

    try:
        logger.info("Initializing and pre-warming YOLO Face model...")
        from preprocessing import get_yolo_face_model
        get_yolo_face_model()
        logger.info("YOLO Face model initialized successfully.")
    except Exception as e:
        logger.warning(f"YOLO Face warmup warning: {e}")

    yield


app = FastAPI(
    title="Utility Bot - Verification Document API",
    version="3.1.0",
    description="Utility Bot backend providing Aadhaar, PAN, and Driving Licence verification with Human-in-the-Loop Confirmation Gateway, 30-day auto-retention, photo storage, and Device ID isolation.",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint reporting OCR & database status."""
    ocr_available, ocr_msg = check_tesseract_available()
    from storage import MONGODB_URI
    return {
        "status": "healthy",
        "service": "utility_bot_backend",
        "ocr_engine": "RapidOCR (ONNX)",
        "ocr_available": ocr_available,
        "ocr_message": ocr_msg,
        "database_connected": True,
        "database_type": "MongoDB Atlas" if MONGODB_URI else "Local Store (history.json)",
        "mongodb_configured": bool(MONGODB_URI),
        "tesseract_available": ocr_available,
        "tesseract_message": ocr_msg
    }


@app.get("/models")
def list_models(api_key: Optional[str] = None):
    """Lists available LLM extraction models."""
    return {"models": get_available_models(api_key)}


@app.get("/history")
def list_history(
    limit: int = 50, 
    page: int = 1, 
    doc_type: Optional[str] = None,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves verified SUCCESS verification records ('IMG...' series) strictly for the public History drawer."""
    active_device = x_device_id or deviceId
    return get_history(limit=limit, page=page, doc_type=doc_type, device_id=active_device)


@app.get("/failed-history")
def list_failed_history(
    limit: int = 50,
    page: int = 1,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves FAILED verification audit records ('FAIL...' series) strictly hidden from public history."""
    active_device = x_device_id or deviceId
    return get_failed_history(limit=limit, page=page, device_id=active_device)


@app.get("/history/{doc_id}")
def retrieve_extraction(
    doc_id: str,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves a single verification record by ID."""
    active_device = x_device_id or deviceId
    record = get_extraction_by_id(doc_id, device_id=active_device)
    if not record:
        raise HTTPException(status_code=404, detail="Document verification record not found or inaccessible for this device.")
    return record


@app.delete("/history/{doc_id}")
def remove_extraction(
    doc_id: str,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Deletes a verification record by ID."""
    active_device = x_device_id or deviceId
    success = delete_extraction_by_id(doc_id, device_id=active_device)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or permission denied.")
    return {"message": "Document deleted successfully."}


@app.get("/storage/stats")
def storage_usage_stats(
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Returns storage usage statistics."""
    active_device = x_device_id or deviceId
    return get_storage_stats(device_id=active_device)


@app.post("/storage/clean")
def trigger_storage_cleanup(
    force_all: bool = False,
    deviceId: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Cleans expired records or purges verification storage."""
    active_device = x_device_id or deviceId
    return clean_storage(device_id=active_device, force_all=force_all)


@app.post("/confirm")
def confirm_verification_decision(
    payload: ConfirmationRequest,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Human-in-the-Loop Confirmation Gateway endpoint:
    - 'correct': Assigns sequential ID 'IMG000001', saves internal record, and generates privacy Identity Reference Card.
    - 'wrong': Assigns sequential ID 'FAIL000001', records audit failure (no reference card created).
    """
    active_device = x_device_id or payload.deviceId or "default_client"
    res = save_confirmed_verification(
        result_dict=payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
        action=payload.action,
        edited_data=payload.data,
        original_filename=payload.original_filename or "document.jpg",
        thumbnail_image=payload.thumbnail_image,
        portrait_photo=payload.portrait_photo,
        device_id=active_device
    )

    # Privacy-Safe Reference Card Generation on User Confirmation
    if payload.action == "correct":
        try:
            from reference_service import create_identity_reference
            clean_data = payload.data or {}
            if hasattr(clean_data, "dict"):
                clean_data = clean_data.dict()
            elif hasattr(clean_data, "model_dump"):
                clean_data = clean_data.model_dump()

            ref_record = create_identity_reference(
                verification_id=res.get("sequential_id") or res.get("id"),
                document_type=payload.document_type,
                extracted_data=clean_data,
                portrait_photo=payload.portrait_photo,
                device_id=active_device
            )
            res["reference_card"] = ref_record
        except Exception as ref_err:
            print(f"[Confirmation] Reference generation notice: {ref_err}")
            res["reference_card"] = None
    else:
        res["reference_card"] = None

    return res


@app.get("/reference/{ref_id}")
def get_public_reference_card(ref_id: str):
    """
    Public QR Verification Endpoint.
    Returns ONLY privacy-safe masked data.
    Never exposes raw unmasked numbers, OCR text, or full document image.
    """
    from reference_service import get_reference_by_id
    rec = get_reference_by_id(ref_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Identity Reference Card not found.")
    return rec


@app.post("/reference/{ref_id}/revoke")
def revoke_public_reference_card(ref_id: str):
    """
    Revokes an active Reference Card so it immediately becomes invalid.
    """
    from reference_service import revoke_reference_by_id
    success = revoke_reference_by_id(ref_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reference card not found or already revoked.")
    return {"message": f"Reference ID {ref_id} has been revoked successfully.", "status": "REVOKED"}


@app.get("/verify/liveness-challenge")
def get_liveness_challenge():
    """Generates an active randomized liveness challenge for camera verification."""
    return generate_liveness_challenge()


@app.post("/verify/live-face")
def verify_live_face(
    payload: LiveFaceVerificationRequest,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Live Camera Face & Liveness Verification Endpoint:
    1. Runs anti-spoofing liveness checks on live webcam selfie.
    2. Extracts deep face embeddings and computes cosine similarity against ID card portrait crop.
    3. Categorizes confidence into 3 calibrated tiers:
       - STRONG_MATCH (>= 75%): Customer Identity Fully Verified (Status: VERIFIED)
       - UNCERTAIN (50% - 74%): Moderate match, suggests Second ID Verification (Status: UNCERTAIN)
       - WEAK (< 50%): Identity Mismatch / Face Verification Failed (Status: FAILED)
    """
    active_device = x_device_id or payload.deviceId or "default_client"

    # 1. Evaluate Liveness / Anti-Spoofing
    liveness_res = evaluate_liveness(
        live_image_input=payload.live_selfie_image,
        challenge_id=payload.challenge_id
    )

    if not liveness_res.get("is_live"):
        return {
            "status": "FAILED",
            "verification_passed": False,
            "overall_tier": "SPOOF_RISK",
            "liveness": liveness_res,
            "face_matching": {
                "match_score": 0.0,
                "match_tier": "WEAK",
                "status": "FAILED",
                "is_matched": False,
                "explanation": "Liveness check failed. Anti-spoofing rejected presentation attack."
            },
            "summary": "Verification Failed: Liveness check rejected. Please ensure proper lighting and avoid digital screens."
        }

    # 2. Compare ID Portrait Face against Live Selfie
    match_res = compare_faces(
        id_portrait_input=payload.id_portrait_photo,
        live_or_second_photo_input=payload.live_selfie_image
    )

    match_tier = match_res.get("match_tier", "WEAK")
    verification_passed = (match_tier == "STRONG_MATCH")

    final_status = "VERIFIED" if match_tier == "STRONG_MATCH" else ("UNCERTAIN" if match_tier == "UNCERTAIN" else "FAILED")

    return {
        "status": final_status,
        "verification_passed": verification_passed,
        "overall_tier": match_tier,
        "liveness": liveness_res,
        "face_matching": match_res,
        "summary": match_res.get("explanation", "")
    }


@app.post("/verify/second-id")
def verify_second_id_crosscheck(
    payload: SecondIdVerificationRequest,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Cross-checks First ID data & portrait against a Second ID document (Aadhaar, PAN, DL).
    Computes fuzzy name match, normalized DOB match, and portrait face similarity.
    Returns structured cross-verification report with status 'DOCUMENTS_CONSISTENT' or 'DOCUMENTS_MISMATCH'.
    """
    active_device = x_device_id or payload.deviceId or "default_client"

    report = cross_verify_documents(
        doc1_data=payload.doc1_data,
        doc2_data=payload.doc2_data,
        doc1_portrait=payload.doc1_portrait,
        doc2_portrait=payload.doc2_portrait,
        doc1_type=payload.doc1_type,
        doc2_type=payload.doc2_type
    )

    return report


@app.post("/extract", response_model=FinalExtractionResult)
async def extract_document(
    file: UploadFile = File(...),
    min_confidence: float = Form(25.0),
    psm_mode: int = Form(11),
    enable_glare: bool = Form(True),
    enable_clahe: bool = Form(True),
    enable_denoise: bool = Form(True),
    enable_threshold: bool = Form(False),
    threshold_method: str = Form("otsu"),
    deep_scan: bool = Form(False),
    model_name: Optional[str] = Form(None),
    groq_api_key: Optional[str] = Form(None),
    deviceId: Optional[str] = Form(None),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Main extraction pipeline endpoint with Pre-LLM Decision Gate.
    1. Reads & validates uploaded image.
    2. Normalizes dimensions for memory safety (max 1600px).
    3. Runs quality & blur assessment.
    4. Runs OpenCV preprocessing (or Deep Multi-Pass Scan).
    5. Runs local RapidOCR & draws bounding boxes.
    6. DECISION GATE: Evaluates document signatures. If unsupported, short-circuits immediately.
    7. Extracts portrait photo thumbnail (YOLO Face / Morphological).
    8. Calls Groq LLM or Pure OCR Regex Engine.
    9. Validates & normalizes fields (Pydantic / Regex).
    10. Returns structured JSON with status='Pending Confirmation'.
    """
    try:
        # 1. Validate file format
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a valid image (JPG, JPEG, PNG).")

        try:
            contents = await file.read()
            pil_image = Image.open(io.BytesIO(contents))
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")
            cv2_orig = pil_to_cv2(pil_image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")

        # 1.1 Memory-Safe Dimension Normalization (Max dimension 1600px)
        h, w = cv2_orig.shape[:2]
        max_dim = 1600
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            cv2_orig = cv2.resize(cv2_orig, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # 2. Image Quality & Blur Check
        quality_report = assess_image_quality(cv2_orig)

        # 3. OpenCV Preprocessing (Standard vs. Deep Multi-Pass)
        if deep_scan:
            logger.info("[Vision Pipeline] Running High-Accuracy Deep Multi-Pass scan...")
            cv2_preprocessed = preprocess_deep_multi_pass(cv2_orig)
        else:
            cv2_preprocessed = preprocess_id_card(
                cv2_orig,
                enable_resize=True,
                enable_clahe=enable_clahe,
                enable_denoise=enable_denoise,
                enable_glare_reduction=enable_glare,
                enable_threshold=enable_threshold,
                threshold_method=threshold_method
            )

        # 4. RapidOCR with Bounding Boxes (Free & Local)
        try:
            ocr_result = extract_ocr_data(
                cv2_preprocessed,
                min_confidence=min_confidence,
                psm_mode=psm_mode
            )
            cv2_annotated = draw_bounding_boxes(cv2_orig, ocr_result, show_confidence=True)
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            raise HTTPException(status_code=500, detail=f"OCR Processing failed: {str(e)}")

        # Encode images for visual pipeline (optimized JPEG quality for fast transmission)
        pipeline_images = {
            "original": cv2_to_base64(cv2_orig, quality=75),
            "preprocessed": cv2_to_base64(cv2_preprocessed, quality=75),
            "annotated": cv2_to_base64(cv2_annotated, quality=80)
        }

        # If no readable text was detected at all
        if ocr_result.word_count == 0 or not ocr_result.raw_text.strip():
            unsupported = UnsupportedDocumentData(
                document_type="unsupported",
                error="No readable text detected in the image. Please verify lighting and focus."
            )
            return FinalExtractionResult(
                document_type="unsupported",
                is_valid=False,
                status="Pending Confirmation",
                short_circuited=True,
                data=unsupported,
                warnings=["No text detected by OCR engine."],
                ocr_confidence=0.0,
                raw_ocr_text="",
                quality_report=quality_report,
                images=pipeline_images,
                portrait_photo=None
            )

        # 5. DECISION GATE: Heuristic Type Check (Pre-LLM Resource Gate)
        heuristic_type, heuristic_conf, heuristic_scores = classify_document_heuristics(ocr_result.raw_text)
        
        # 6. Portrait Face Crop Extraction (Only Once, Type-Aware)
        portrait_photo = None
        if heuristic_type not in ["aadhaar_back", "pan_back", "driving_licence_back", "unsupported"]:
            try:
                portrait_photo = extract_portrait_photo(cv2_orig, doc_type_hint=heuristic_type)
            except Exception as face_err:
                logger.warning(f"Face extraction notice: {face_err}")
                portrait_photo = None

        # If the document shows NO resemblance to Aadhaar, PAN, or DL, short-circuit immediately
        if heuristic_type == "unsupported" and max(heuristic_scores.values()) == 0:
            logger.info("[Decision Gate] Document rejected before LLM call. Zero ID keywords found.")
            unsupported = UnsupportedDocumentData(
                document_type="unsupported",
                error="Decision Gate: Document does not match Indian Aadhaar, PAN, or Driving Licence patterns. LLM processing skipped."
            )
            return FinalExtractionResult(
                document_type="unsupported",
                is_valid=False,
                status="Pending Confirmation",
                short_circuited=True,
                data=unsupported,
                warnings=["Rejected by Pre-LLM Decision Gate (Non-ID document detected)."],
                ocr_confidence=ocr_result.average_confidence,
                raw_ocr_text=ocr_result.raw_text,
                quality_report=quality_report,
                images=pipeline_images,
                portrait_photo=None
            )

        # 7. Groq LLM API Call (Only for supported IDs)
        heuristic_hint_str = f"Found pattern matching for: {heuristic_type.upper()}" if heuristic_type != "unsupported" else None
        
        raw_llm_json, llm_error = extract_document_info(
            ocr_raw_text=ocr_result.raw_text,
            ocr_layout_text=ocr_result.layout_text,
            api_key=groq_api_key,
            model_name=model_name,
            heuristic_hint=heuristic_hint_str
        )

        detected_doc_type = raw_llm_json.get("document_type") or heuristic_type
        if raw_llm_json.get("document_type") == "unsupported" and heuristic_type != "unsupported":
            raw_llm_json["document_type"] = heuristic_type
            detected_doc_type = heuristic_type

        # Re-evaluate portrait photo if doc type was refined or back side detected
        if detected_doc_type in ["aadhaar_back", "pan_back", "driving_licence_back", "unsupported"]:
            portrait_photo = None
        elif not portrait_photo:
            portrait_photo = extract_portrait_photo(cv2_orig, doc_type_hint=detected_doc_type)

        # 8. Post-Validation and Pydantic Normalization
        final_result = validate_and_clean_extraction(
            raw_data=raw_llm_json,
            ocr_confidence=ocr_result.average_confidence,
            raw_ocr_text=ocr_result.raw_text,
            quality_report=quality_report,
            images=pipeline_images,
            short_circuited=False,
            portrait_photo=portrait_photo
        )

        return final_result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Extract Exception] {exc}", exc_info=True)
        unsupported = UnsupportedDocumentData(
            document_type="unsupported",
            error=f"Processing failed: {str(exc)}"
        )
        return FinalExtractionResult(
            document_type="unsupported",
            is_valid=False,
            status="Pending Confirmation",
            short_circuited=True,
            data=unsupported,
            warnings=[f"Error during extraction: {str(exc)}"],
            ocr_confidence=0.0,
            raw_ocr_text="",
            quality_report={"blur_score": 0.0, "is_blurry": False, "width": 0, "height": 0, "is_too_small": False},
            images={"original": "", "preprocessed": "", "annotated": ""},
            portrait_photo=None
        )


@app.post("/extract-shipping", response_model=List[ShippingLabelResult])
async def extract_shipping_labels(
    files: List[UploadFile] = File(...),
    min_confidence: float = Form(20.0),
    enable_clahe: bool = Form(True),
    enable_denoise: bool = Form(True),
    model_name: Optional[str] = Form(None),
    groq_api_key: Optional[str] = Form(None)
):
    """
    Multi-Image Shipping Label Extraction Endpoint.
    Accepts 1 to 3 images (JPG, JPEG, PNG).
    Processes every image separately without merging.
    Runs RapidOCR, sends OCR output to LLM to understand and separate
    data into FROM, TO, Order, Package, Items, and scans Barcodes & QR codes.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least 1 shipping label image is required.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 shipping label images allowed per batch request.")

    results: List[ShippingLabelResult] = []

    for idx, file in enumerate(files, start=1):
        filename = file.filename or f"shipping_label_{idx}.jpg"

        # 1. Format check
        if not file.content_type or not file.content_type.startswith("image/"):
            res = ShippingLabelResult(
                image_name=filename,
                image_index=idx,
                warnings=[f"File '{filename}' must be a valid image (JPG, JPEG, PNG)."]
            )
            results.append(res)
            continue

        try:
            contents = await file.read()
            pil_image = Image.open(io.BytesIO(contents))
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")
            cv2_orig = pil_to_cv2(pil_image)
        except Exception as e:
            res = ShippingLabelResult(
                image_name=filename,
                image_index=idx,
                warnings=[f"Failed to decode image '{filename}': {str(e)}"]
            )
            results.append(res)
            continue

        # 2. Memory-safe dimension normalization (Max dim 1800px)
        h, w = cv2_orig.shape[:2]
        max_dim = 1800
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            cv2_orig = cv2.resize(cv2_orig, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # 3. Barcode & QR Code detection
        codes_dict = extract_codes(cv2_orig)

        # 4. OpenCV Preprocessing for OCR
        try:
            cv2_preprocessed = preprocess_id_card(
                cv2_orig,
                enable_resize=False,
                enable_clahe=enable_clahe,
                enable_denoise=enable_denoise,
                enable_glare_reduction=True
            )
        except Exception:
            cv2_preprocessed = cv2_orig

        # 5. RapidOCR Text Extraction
        try:
            ocr_res = extract_ocr_data(cv2_preprocessed, min_confidence=min_confidence)
            ocr_raw_text = ocr_res.raw_text
            ocr_layout_text = ocr_res.layout_text
            ocr_conf = ocr_res.average_confidence
            ocr_words = [w.dict() if hasattr(w, "dict") else w.model_dump() for w in ocr_res.words]
        except Exception as ocr_err:
            logger.error(f"OCR error on {filename}: {ocr_err}")
            ocr_raw_text = ""
            ocr_layout_text = ""
            ocr_conf = 0.0
            ocr_words = []

        raw_barcodes = codes_dict.get("barcodes", [])
        raw_qrcodes = codes_dict.get("qr_codes", [])

        # 6. Extract Shipping Fields via LLM (RapidOCR output -> LLM understands & separates data)
        label_res = extract_shipping_info_llm(
            ocr_raw_text=ocr_raw_text,
            ocr_layout_text=ocr_layout_text,
            ocr_words=ocr_words,
            api_key=groq_api_key,
            model_name=model_name,
            barcodes=raw_barcodes,
            qr_codes=raw_qrcodes
        )

        label_res.image_name = filename
        label_res.image_index = idx
        label_res.ocr_confidence = ocr_conf
        label_res.barcodes = [CodeItem(**c) for c in raw_barcodes]
        label_res.qr_codes = [CodeItem(**c) for c in raw_qrcodes]

        results.append(label_res)

    return results


# =============================================================================
# QR Code Generator & Standalone Optical Scanner Endpoints
# =============================================================================

from pydantic import BaseModel, Field

class QRGenerateRequest(BaseModel):
    type: str = Field(default="text", description="QR payload type: text, url, phone, email, sms, wifi, vcard, location, product, order, shipping, json")
    data: Optional[Any] = Field(default=None, description="Direct text or payload string")
    fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured fields for specialized QR types (e.g. ssid, password, vcard info)")
    size: int = Field(default=400, ge=100, le=2400, description="Image dimension in pixels (e.g. 200, 400, 600, 800, 1200)")
    error_correction: str = Field(default="M", description="Error correction level: L (7%), M (15%), Q (25%), H (30%)")
    format: str = Field(default="png", description="Output format: png or svg")


@app.post("/generate-qr")
@app.post("/generate-qr/")
def generate_qr_code_endpoint(payload: QRGenerateRequest):
    """
    Standalone QR Code Generator & Verification Endpoint.
    Formats 12 standardized payload types (URL, Wi-Fi, vCard, SMS, Email, Location, Shipping, JSON),
    checks data capacity, selects optimal QR version, renders PNG/SVG, and auto-verifies readability.
    """
    try:
        from qr_generator import generate_and_verify_qr
        result = generate_and_verify_qr(
            qr_type=payload.type,
            data=payload.data,
            fields=payload.fields,
            size=payload.size,
            error_correction=payload.error_correction,
            output_format=payload.format
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"QR Generation error: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to generate QR Code: {str(exc)}")


@app.post("/scan-code")
@app.post("/scan-code/")
async def scan_optical_code_endpoint(file: UploadFile = File(...)):
    """
    Standalone QR & Barcode Scanner Endpoint.
    Upload 1 image (JPG, JPEG, PNG). Runs multi-pass ZXing-CPP + OpenCV reader across 11+ formats
    and separates QR codes from 1D linear barcodes.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="An image file is required.")

    filename = file.filename
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents))
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        cv2_img = pil_to_cv2(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format for '{filename}': {str(e)}")

    codes_dict = extract_codes(cv2_img)
    qr_list = codes_dict.get("qr_codes", [])
    bar_list = codes_dict.get("barcodes", [])

    return {
        "success": True,
        "filename": filename,
        "qr_codes": qr_list,
        "barcodes": bar_list,
        "total_detected": len(qr_list) + len(bar_list)
    }


@app.post("/scan-document-codes")
@app.post("/scan-document-codes/")
async def scan_document_codes_endpoint(
    file: UploadFile = File(...),
    min_confidence: float = Form(20.0)
):
    """
    Combined OCR + QR + Barcode Document Scanning Endpoint.
    Simultaneously extracts printed document text via RapidOCR and detects all optical codes (QR & Barcodes).
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="An image file is required.")

    filename = file.filename
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents))
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        cv2_img = pil_to_cv2(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format for '{filename}': {str(e)}")

    # 1. Barcode & QR Code extraction
    codes_dict = extract_codes(cv2_img)
    qr_list = codes_dict.get("qr_codes", [])
    bar_list = codes_dict.get("barcodes", [])

    # 2. RapidOCR Text Extraction
    annotated_image_b64 = None
    try:
        ocr_res = extract_ocr_data(cv2_img, min_confidence=min_confidence)
        annotated_cv2 = draw_bounding_boxes(cv2_img, ocr_res, show_confidence=True)
        annotated_image_b64 = cv2_to_base64(annotated_cv2)
        ocr_data = {
            "raw_text": ocr_res.raw_text,
            "confidence": round(ocr_res.average_confidence, 1),
            "word_count": len(ocr_res.words)
        }
    except Exception as ocr_err:
        logger.warning(f"OCR scan warning on {filename}: {ocr_err}")
        ocr_data = {
            "raw_text": "",
            "confidence": 0.0,
            "word_count": 0
        }

    return {
        "success": True,
        "filename": filename,
        "ocr": ocr_data,
        "annotated_image": annotated_image_b64,
        "qr_codes": qr_list,
        "barcodes": bar_list,
        "total_detected": len(qr_list) + len(bar_list)
    }



# -----------------------------------------------------------------------------
# Unified Full-Stack Serving: React Client + FastAPI Backend in One Service
# -----------------------------------------------------------------------------
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "client", "dist")
if not os.path.exists(DIST_DIR):
    DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(DIST_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend not built. Run 'npm run build' in client directory.")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
