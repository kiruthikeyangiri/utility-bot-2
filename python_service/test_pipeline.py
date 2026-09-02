"""
test_pipeline.py - Verification test suite for ID Card Extractor modules.
Tests preprocessing, validation rules, regex checks, schemas, and classification heuristics.
"""

import sys
import numpy as np
import cv2

from schemas import (
    AadhaarData,
    PANData,
    DrivingLicenceData,
    UnsupportedDocumentData,
    OCRResult,
    BoundingBox
)
from validation import (
    normalize_date,
    validate_and_mask_aadhaar,
    validate_pan,
    validate_driving_licence,
    validate_and_clean_extraction,
    clean_name,
    sanitize_gender
)
from preprocessing import (
    assess_image_quality,
    preprocess_id_card,
    to_grayscale,
    enhance_contrast
)
from document_classifier import classify_document_heuristics
from utils import format_json_output


def test_date_normalization():
    print("Testing Date Normalization...")
    d1, _ = normalize_date("15/08/2002")
    assert d1 == "2002-08-15", f"Expected 2002-08-15, got {d1}"

    d2, _ = normalize_date("01-01-1995")
    assert d2 == "1995-01-01", f"Expected 1995-01-01, got {d2}"

    d3, _ = normalize_date("1990-12-31")
    assert d3 == "1990-12-31", f"Expected 1990-12-31, got {d3}"

    d4, _ = normalize_date(None)
    assert d4 is None
    print("  [PASS] Date Normalization tests passed.")


def test_pan_validation():
    print("Testing PAN Validation...")
    pan_valid, w1 = validate_pan("abcpe1234f")
    assert pan_valid == "ABCPE1234F", f"Expected ABCPE1234F, got {pan_valid}"
    assert len(w1) == 0, f"Expected no warnings, got {w1}"

    pan_invalid, w2 = validate_pan("12345ABCDE")
    assert len(w2) > 0, "Expected warning for invalid PAN format"
    print("  [PASS] PAN Validation tests passed.")


def test_aadhaar_validation():
    print("Testing Aadhaar Validation & Masking...")
    masked1, w1 = validate_and_mask_aadhaar("1234 5678 9010")
    assert masked1 == "********9010", f"Expected ********9010, got {masked1}"
    assert len(w1) == 0

    masked2, _ = validate_and_mask_aadhaar("987654321096")
    assert masked2 == "********1096", f"Expected ********1096, got {masked2}"

    _, w3 = validate_and_mask_aadhaar("12345")
    assert len(w3) > 0, "Expected warning for invalid Aadhaar"
    print("  [PASS] Aadhaar Validation tests passed.")


def test_driving_licence_validation():
    print("Testing Driving Licence Validation...")
    dl, w = validate_driving_licence("TN-01-20220012345")
    assert "TN" in dl
    print("  [PASS] Driving Licence Validation tests passed.")


def test_document_classification_heuristics():
    print("Testing Heuristic Document Classifier...")
    aadhaar_text = "Government of India Unique Identification Authority of India 1234 5678 9012"
    doc_type1, conf1, _ = classify_document_heuristics(aadhaar_text)
    assert doc_type1 == "aadhaar", f"Expected aadhaar, got {doc_type1}"

    pan_text = "INCOME TAX DEPARTMENT GOVT OF INDIA PERMANENT ACCOUNT NUMBER ABCDE1234F"
    doc_type2, conf2, _ = classify_document_heuristics(pan_text)
    assert doc_type2 == "pan", f"Expected pan, got {doc_type2}"

    dl_text = "UNION OF INDIA DRIVING LICENCE FORM 7 DL NO TN0120220012345"
    doc_type3, conf3, _ = classify_document_heuristics(dl_text)
    assert doc_type3 == "driving_licence", f"Expected driving_licence, got {doc_type3}"

    unsupported_text = "Coffee Shop Receipt Total $15.00 Thank you"
    doc_type4, conf4, _ = classify_document_heuristics(unsupported_text)
    assert doc_type4 == "unsupported", f"Expected unsupported, got {doc_type4}"
    print("  [PASS] Heuristic Classification tests passed.")


def test_preprocessing_synthetic():
    print("Testing OpenCV Preprocessing Pipeline...")
    synthetic_img = np.ones((500, 800, 3), dtype=np.uint8) * 255
    cv2.putText(synthetic_img, "GOVERNMENT OF INDIA", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(synthetic_img, "SURESH KUMAR", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    quality = assess_image_quality(synthetic_img)
    assert quality["width"] == 800
    assert quality["height"] == 500

    processed = preprocess_id_card(synthetic_img)
    assert len(processed.shape) == 2
    assert processed.shape[1] == 1800
    print("  [PASS] OpenCV Preprocessing tests passed.")


def test_full_validation_flow():
    print("Testing End-to-End Extraction Result Assembly...")
    raw_aadhaar_llm = {
        "document_type": "aadhaar",
        "name": "Suresh Kumar",
        "date_of_birth": "15/08/2002",
        "gender": "male",
        "aadhaar_number": "1234 5678 9012",
        "address": "22 Anna Nagar, Chennai"
    }
    result = validate_and_clean_extraction(raw_aadhaar_llm, ocr_confidence=92.5)
    assert result.document_type == "aadhaar"
    assert result.is_valid is True
    assert result.data.aadhaar_number == "********9012"
    assert result.data.date_of_birth == "2002-08-15"
    assert result.data.gender == "Male"

    json_str = format_json_output(result)
    assert "********9012" in json_str
    print("  [PASS] Extraction Result Assembly passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING ID EXTRACTOR MODULE TESTS")
    print("=" * 60)
    test_date_normalization()
    test_pan_validation()
    test_aadhaar_validation()
    test_driving_licence_validation()
    test_document_classification_heuristics()
    test_preprocessing_synthetic()
    test_full_validation_flow()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! [SUCCESS]")
    print("=" * 60)
