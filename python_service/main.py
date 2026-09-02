"""
main.py - FastAPI Microservice for ID Card Information Extraction.
Exposes REST endpoints for image preprocessing, OCR, Decision Gate check,
Groq LLM extraction, and Pydantic validation.
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

from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from schemas import FinalExtractionResult, UnsupportedDocumentData
from preprocessing import assess_image_quality, preprocess_id_card
from ocr_engine import extract_ocr_data, draw_bounding_boxes, check_tesseract_available, get_ocr_reader
from document_classifier import classify_document_heuristics
from llm_extractor import extract_document_info, get_available_models
from validation import validate_and_clean_extraction
from utils import pil_to_cv2, cv2_to_base64, logger
from storage import save_extraction, get_history, get_extraction_by_id, delete_extraction_by_id, get_storage_stats, clean_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warms OCR reader on startup to guarantee instant extraction requests."""
    logger.info("Initializing and pre-warming RapidOCR ONNX engine...")
    try:
        get_ocr_reader()
        logger.info("RapidOCR engine initialized successfully.")
    except Exception as e:
        logger.warning(f"RapidOCR warmup warning: {e}")
    yield


app = FastAPI(
    title="Utility Bot - Verification Document API",
    version="3.0.0",
    description="Utility Bot backend providing Aadhaar, PAN, and Driving Licence verification with 30-day auto-retention, photo storage, and Device ID isolation.",
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
    """Retrieves available Groq chat completion models."""
    try:
        models = get_available_models(api_key)
        return {"status": "success", "models": models}
    except Exception as e:
        return {"status": "error", "message": str(e), "models": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]}


@app.get("/history")
def list_history(
    limit: int = 50, 
    page: int = 1, 
    type: Optional[str] = None,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    deviceId: Optional[str] = Query(None)
):
    """Retrieves stored verification records with 30-day auto-retention filtered by Device ID."""
    active_device = x_device_id or deviceId
    return get_history(limit=limit, page=page, doc_type=type, device_id=active_device)


@app.get("/history/{doc_id}")
def get_single_history(
    doc_id: str,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Retrieves single extraction record by ID."""
    doc = get_extraction_by_id(doc_id, device_id=x_device_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/history/{doc_id}")
def delete_single_history(
    doc_id: str,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Deletes extraction record by ID."""
    success = delete_extraction_by_id(doc_id, device_id=x_device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully", "id": doc_id}


@app.get("/storage/stats")
def storage_stats(
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Returns database and local storage capacity metrics (30-day retention)."""
    return get_storage_stats(device_id=x_device_id)


@app.post("/storage/clean")
def trigger_storage_cleanup(
    force_all: bool = False,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """Cleans expired records or purges verification storage."""
    return clean_storage(device_id=x_device_id, force_all=force_all)


@app.post("/extract", response_model=FinalExtractionResult)
def extract_document(
    file: UploadFile = File(...),
    min_confidence: float = Form(25.0),
    psm_mode: int = Form(11),
    enable_glare: bool = Form(True),
    enable_clahe: bool = Form(True),
    enable_denoise: bool = Form(True),
    enable_threshold: bool = Form(False),
    threshold_method: str = Form("otsu"),
    model_name: Optional[str] = Form(None),
    groq_api_key: Optional[str] = Form(None),
    deviceId: Optional[str] = Form(None),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id")
):
    """
    Main extraction pipeline endpoint with Pre-LLM Decision Gate.
    
    1. Reads & validates uploaded image.
    2. Runs quality & blur assessment.
    3. Runs OpenCV preprocessing.
    4. Runs local OCR & draws bounding boxes.
    5. DECISION GATE: Evaluates document signatures. If unsupported, skips LLM call immediately.
    6. Calls Groq LLM or Pure OCR Regex Engine.
    7. Validates & normalizes fields (Pydantic / Regex).
    8. Returns structured JSON + base64 visual pipeline images.
    """
    # 1. Validate file format
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image (JPG, JPEG, PNG).")

    try:
        contents = file.file.read()
        pil_image = Image.open(io.BytesIO(contents))
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        cv2_orig = pil_to_cv2(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")

    # 2. Image Quality & Blur Check
    quality_report = assess_image_quality(cv2_orig)

    # 3. OpenCV Preprocessing
    cv2_preprocessed = preprocess_id_card(
        cv2_orig,
        enable_resize=True,
        enable_clahe=enable_clahe,
        enable_denoise=enable_denoise,
        enable_glare_reduction=enable_glare,
        enable_threshold=enable_threshold,
        threshold_method=threshold_method
    )

    # 4. Tesseract OCR with Bounding Boxes (Free & Local)
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

    # Encode images for visual pipeline
    pipeline_images = {
        "original": cv2_to_base64(cv2_orig, quality=80),
        "preprocessed": cv2_to_base64(cv2_preprocessed, quality=80),
        "annotated": cv2_to_base64(cv2_annotated, quality=85)
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
            short_circuited=True,
            data=unsupported,
            warnings=["No text detected by OCR engine."],
            ocr_confidence=0.0,
            raw_ocr_text="",
            quality_report=quality_report,
            images=pipeline_images
        )

    # 5. DECISION GATE: Heuristic Type Check (Pre-LLM Resource Gate)
    heuristic_type, heuristic_conf, heuristic_scores = classify_document_heuristics(ocr_result.raw_text)
    
    # If the document shows NO resemblance to Aadhaar, PAN, or DL, short-circuit immediately
    if heuristic_type == "unsupported" and max(heuristic_scores.values()) == 0:
        logger.info("[Decision Gate] Document rejected before LLM call. Zero ID keywords found.")
        unsupported = UnsupportedDocumentData(
            document_type="unsupported",
            error="Decision Gate: Document does not match Indian Aadhaar, PAN, or Driving Licence patterns. LLM processing skipped."
        )
        res = FinalExtractionResult(
            document_type="unsupported",
            is_valid=False,
            short_circuited=True,
            data=unsupported,
            warnings=["Rejected by Pre-LLM Decision Gate (Non-ID document detected)."],
            ocr_confidence=ocr_result.average_confidence,
            raw_ocr_text=ocr_result.raw_text,
            quality_report=quality_report,
            images=pipeline_images
        )
        active_device = x_device_id or deviceId or "default_client"
        res.id = save_extraction(
            result_dict=res.model_dump() if hasattr(res, 'model_dump') else res.dict(),
            original_filename=file.filename or "document.jpg",
            thumbnail_image=pipeline_images.get("original"),
            device_id=active_device
        )
        return res

    # 6. Groq LLM API Call (Only for supported IDs)
    heuristic_hint_str = f"Found pattern matching for: {heuristic_type.upper()}" if heuristic_type != "unsupported" else None
    
    raw_llm_json, llm_error = extract_document_info(
        ocr_raw_text=ocr_result.raw_text,
        ocr_layout_text=ocr_result.layout_text,
        api_key=groq_api_key,
        model_name=model_name,
        heuristic_hint=heuristic_hint_str
    )

    if raw_llm_json.get("document_type") == "unsupported" and heuristic_type != "unsupported":
        raw_llm_json["document_type"] = heuristic_type

    # 7. Post-Validation and Pydantic Normalization
    final_result = validate_and_clean_extraction(
        raw_data=raw_llm_json,
        ocr_confidence=ocr_result.average_confidence,
        raw_ocr_text=ocr_result.raw_text,
        quality_report=quality_report,
        images=pipeline_images,
        short_circuited=False
    )

    # 8. Save extraction to persistent history store with 30-day retention, photo thumbnail & device isolation
    active_device = x_device_id or deviceId or "default_client"
    doc_id = save_extraction(
        result_dict=final_result.model_dump() if hasattr(final_result, 'model_dump') else final_result.dict(),
        original_filename=file.filename or "document.jpg",
        thumbnail_image=pipeline_images.get("original"),
        device_id=active_device
    )
    final_result.id = doc_id

    return final_result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
