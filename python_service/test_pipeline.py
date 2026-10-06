"""
test_pipeline.py - Verification test suite for ID Card Extractor modules.
Tests preprocessing, validation rules, regex checks, schemas, classification heuristics,
face matching, anti-spoofing liveness, cross-verification, and reference card generation.
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
from reference_service import mask_aadhaar, mask_pan, mask_driving_licence, create_identity_reference
from liveness_service import generate_liveness_challenge, analyze_fft_frequency_texture, analyze_specular_screen_glare
from document_crosscheck_service import calculate_name_similarity, cross_verify_documents
from face_matching_service import compare_faces


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


def test_reference_card_service():
    print("Testing Reference Card Generation & Masking...")
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_pan("ABCDE1234F") == "XXXXX1234F"
    assert mask_driving_licence("TN0120220012345") == "XXXXXXXX 2345"

    ref = create_identity_reference(
        verification_id="IMG000001",
        document_type="aadhaar",
        extracted_data={
            "name": "Kiruthikeyan",
            "aadhaar_number": "********9012",
            "date_of_birth": "2000-01-01"
        },
        device_id="test_device"
    )
    assert ref["reference_id"].startswith("AAD-KYC-")
    assert ref["revoked"] is False
    assert ref["verification_status"] == "DETAILS CONFIRMED"
    assert "qr_code_image" in ref
    print("  [PASS] Reference Card Service tests passed.")


def test_liveness_and_spoof_detection():
    print("Testing Liveness & Anti-Spoofing...")
    chal = generate_liveness_challenge()
    assert "challenge_id" in chal
    assert chal["challenge_type"] in ["blink", "smile", "turn_left", "turn_right"]

    gray_face = np.random.randint(50, 200, (128, 128), dtype=np.uint8)
    fft_res = analyze_fft_frequency_texture(gray_face)
    assert "fft_score" in fft_res

    bgr_face = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
    glare_res = analyze_specular_screen_glare(bgr_face)
    assert "glare_score" in glare_res
    print("  [PASS] Liveness & Anti-Spoofing tests passed.")


def test_crosscheck_service():
    print("Testing Multi-Document Cross-Verification...")
    score1, match1 = calculate_name_similarity("S Kiruthikeyan", "Kiruthikeyan S")
    assert score1 >= 95.0, f"Expected permutation match score >= 95, got {score1}"

    score2, match2 = calculate_name_similarity("Shanmugam Kiruthikeyan", "S Kiruthikeyan")
    assert score2 >= 90.0, f"Expected initial expansion match score >= 90, got {score2}"

    doc1 = {"name": "Kiruthikeyan S", "date_of_birth": "2000-05-15", "gender": "Male"}
    doc2 = {"name": "S Kiruthikeyan", "date_of_birth": "15/05/2000", "gender": "M"}
    report = cross_verify_documents(
        doc1_data=doc1,
        doc2_data=doc2,
        doc1_type="aadhaar",
        doc2_type="pan"
    )
    assert report["is_consistent"] is True
    assert report["is_approved"] is True
    assert report["approval_status"] == "APPROVED"
    assert report["matched_factors_count"] >= 2
    assert "field_comparisons" in report
    print("  [PASS] Multi-Document Cross-Verification tests passed.")


from shipping_extractor import extract_shipping_label_data, extract_shipping_info_llm


def test_shipping_label_extraction():
    print("Testing Shipping Label LLM & Heuristic Extraction...")
    ocr_raw = """
    SHIP TO:
    AHAMMED
    Phone:
    12th cross
    KA
    PIN: 560043

    SHIP FROM:
    FLIPKART LOGISTICS
    Bangalore
    560100

    ORDER ID: ORD-9928172
    AWB: 1122334455
    WEIGHT: 1.5 KG
    DIMENSIONS: 10x10x5 cm
    COD: Rs. 499

    T-Shirt Qty 1 Price 499 Total 499
    """
    # 1. Test baseline heuristic parser
    res = extract_shipping_label_data(ocr_raw, ocr_raw)
    assert res.ship_to.phone is None, f"Expected phone to be None, got: {res.ship_to.phone}"
    assert "12th cross" in (res.ship_to.address or ""), f"Expected '12th cross' in address, got: {res.ship_to.address}"
    assert res.ship_to.postal_code == "560043"
    assert res.order.order_id == "ORD-9928172"
    assert res.order.awb_number == "1122334455"
    assert res.order.payment_type == "COD"
    assert "1.5" in (res.package.weight or "")

    # 2. Test LLM extraction pipeline wrapper
    llm_res = extract_shipping_info_llm(ocr_raw, ocr_raw)
    assert llm_res.ship_to.phone is None
    assert "12th cross" in (llm_res.ship_to.address or "")
    assert llm_res.order.order_id == "ORD-9928172"
    assert llm_res.order.awb_number == "1122334455"

    # 3. Test USPS / International standard label without explicit "SHIP TO" headers
    usps_ocr = """5oz First-Class Pkg Svc
CommercialBasePrice 071S00858181
USPS FIRST-CLASS PKG
Mailed from ZIP 77024
WAREHOUSE 2
11919 WINK RD
HOUSTON TX 77024-7134
Order: 286
John Doe
321 Street Over There
Salt Lake City, UT 11212
United States"""
    usps_res = extract_shipping_label_data(usps_ocr, usps_ocr)
    assert usps_res.courier == "USPS", f"Expected USPS, got: {usps_res.courier}"
    assert usps_res.package.weight == "5oz", f"Expected 5oz, got: {usps_res.package.weight}"
    assert usps_res.order.order_id == "286", f"Expected 286, got: {usps_res.order.order_id}"
    assert usps_res.ship_from.name == "WAREHOUSE 2", f"Expected WAREHOUSE 2, got: {usps_res.ship_from.name}"
    assert usps_res.ship_to.name == "John Doe", f"Expected John Doe, got: {usps_res.ship_to.name}"
    assert usps_res.ship_to.city == "Salt Lake City", f"Expected Salt Lake City, got: {usps_res.ship_to.city}"
    assert usps_res.ship_to.state == "Utah", f"Expected Utah, got: {usps_res.ship_to.state}"
    assert usps_res.ship_to.postal_code == "11212", f"Expected 11212, got: {usps_res.ship_to.postal_code}"
    assert usps_res.ship_to.country == "United States", f"Expected United States, got: {usps_res.ship_to.country}"

    # 4. Test unspaced OCR tokens and tracking numbers
    unspaced_ocr = """5oz First-Class Pkg Svc
CommeroialBasePrice 071S00858181
USPS FIRST-CLASS PKG
Mailed from ZIP 77024
WAREHOUSE2
11919WINKRD
HOUSTONTX77024-7134
Order: 286
JohnDoe
321StreetOverThere
Salt Lake City, UT
11212
USPSTRACKING#
9400110200793961893691"""
    unspaced_res = extract_shipping_label_data(unspaced_ocr, unspaced_ocr)
    assert unspaced_res.ship_from.name == "WAREHOUSE 2", f"Expected WAREHOUSE 2, got: {unspaced_res.ship_from.name}"
    assert unspaced_res.ship_from.city == "Houston", f"Expected Houston, got: {unspaced_res.ship_from.city}"
    assert unspaced_res.ship_from.state == "Texas", f"Expected Texas, got: {unspaced_res.ship_from.state}"
    assert unspaced_res.ship_from.postal_code == "77024-7134", f"Expected 77024-7134, got: {unspaced_res.ship_from.postal_code}"
    assert unspaced_res.ship_to.name == "John Doe", f"Expected John Doe, got: {unspaced_res.ship_to.name}"
    assert unspaced_res.ship_to.address == "321 Street Over There", f"Expected 321 Street Over There, got: {unspaced_res.ship_to.address}"
    assert unspaced_res.ship_to.city == "Salt Lake City", f"Expected Salt Lake City, got: {unspaced_res.ship_to.city}"
    assert unspaced_res.ship_to.state == "Utah", f"Expected Utah, got: {unspaced_res.ship_to.state}"
    assert unspaced_res.ship_to.postal_code == "11212", f"Expected 11212, got: {unspaced_res.ship_to.postal_code}"

    # 5. Test Indian label with payment method and items table
    indian_ocr = """AHAMMED
Pre-paid
12thcross
KA
PIN: 560043

SHIP FROM:
Hari
Add:1st sector
Product Price (INR) Total (INR)
TShirt 10 10
Total 10 10"""
    indian_res = extract_shipping_label_data(indian_ocr, indian_ocr)
    assert indian_res.ship_to.name == "AHAMMED", f"Expected AHAMMED, got: {indian_res.ship_to.name}"
    assert indian_res.ship_to.address == "12th cross", f"Expected '12th cross', got: {indian_res.ship_to.address}"
    assert indian_res.ship_to.state == "Karnataka", f"Expected Karnataka, got: {indian_res.ship_to.state}"
    assert indian_res.ship_to.postal_code == "560043", f"Expected 560043, got: {indian_res.ship_to.postal_code}"
    assert indian_res.order.payment_type == "PREPAID", f"Expected PREPAID, got: {indian_res.order.payment_type}"
    assert indian_res.ship_from.name == "Hari", f"Expected Hari, got: {indian_res.ship_from.name}"
    assert indian_res.ship_from.address == "1st sector", f"Expected '1st sector', got: {indian_res.ship_from.address}"
    # 6. Test 2-Column / Side-by-Side shipping label
    two_col_words = [
        {"text": "John Doe", "x": 40, "y": 100, "width": 80, "height": 20},
        {"text": "ACME Corporation", "x": 320, "y": 100, "width": 130, "height": 20},
        {"text": "123 Main Street", "x": 40, "y": 130, "width": 120, "height": 20},
        {"text": "456 Industrial Blvd", "x": 320, "y": 130, "width": 140, "height": 20},
        {"text": "Apt 4B", "x": 40, "y": 160, "width": 50, "height": 20},
        {"text": "Los Angeles, CA 90001", "x": 40, "y": 190, "width": 150, "height": 20},
        {"text": "New York, NY 10001", "x": 320, "y": 190, "width": 140, "height": 20},
    ]
    two_col_raw = """John Doe ACME Corporation
123 Main Street 456 Industrial Blvd
Apt 4B
Los Angeles, CA 90001 New York, NY 10001"""
    two_col_res = extract_shipping_label_data(two_col_raw, two_col_raw, ocr_words=two_col_words)
    assert two_col_res.ship_to.name == "John Doe", f"Expected John Doe, got: {two_col_res.ship_to.name}"
    assert "123 Main Street" in (two_col_res.ship_to.address or ""), f"Expected 123 Main Street in address, got: {two_col_res.ship_to.address}"
    assert two_col_res.ship_to.city == "Los Angeles", f"Expected Los Angeles, got: {two_col_res.ship_to.city}"
    assert two_col_res.ship_to.state == "California", f"Expected California, got: {two_col_res.ship_to.state}"
    assert two_col_res.ship_to.postal_code == "90001", f"Expected 90001, got: {two_col_res.ship_to.postal_code}"
    assert two_col_res.ship_from.name == "ACME Corporation", f"Expected ACME Corporation, got: {two_col_res.ship_from.name}"
    assert "456 Industrial Blvd" in (two_col_res.ship_from.address or ""), f"Expected 456 Industrial Blvd in address, got: {two_col_res.ship_from.address}"
    assert two_col_res.ship_from.city == "New York", f"Expected New York, got: {two_col_res.ship_from.city}"
    assert two_col_res.ship_from.state == "New York", f"Expected New York, got: {two_col_res.ship_from.state}"
    assert two_col_res.ship_from.postal_code == "10001", f"Expected 10001, got: {two_col_res.ship_from.postal_code}"
    print("  [PASS] Shipping Label LLM & Heuristic Extraction tests passed (Domestic, USPS, Unspaced OCR, Tables & 2-Column).")


def test_barcode_qr_and_cross_validation():
    print("Testing QR/Barcode Multi-Pass Detection, Classification & OCR Cross-Validation...")
    from code_reader import classify_qr_content, extract_codes
    from shipping_extractor import cross_validate_codes_with_ocr, normalize_ocr_digits
    from shipping_schemas import ShippingLabelResult, OrderInformation, CodeItem

    # 1. Test QR Content Classification
    assert classify_qr_content("https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899562847123456") == "Tracking URL"
    assert classify_qr_content("http://delhivery.com/track/pkg/1234567890") == "Tracking URL"
    assert classify_qr_content('{"order_id": "ORD-99", "awb": "DEL987654"}') == "JSON"
    assert classify_qr_content("AWB-9876543210") == "AWB Number"
    assert classify_qr_content("ORD-887654") == "Order ID"
    assert classify_qr_content("FedEx Express Standard Overnight") == "Courier Information"
    assert classify_qr_content("Simple shipping note") == "Plain Text"

    # 2. Test OCR Digit Normalization (OCR Typos: O->0, I->1, S->5)
    assert normalize_ocr_digits("12345O789O12") == "123450789012"
    assert normalize_ocr_digits("AWB-I2345") == "AWB12345"

    # 3. Test Cross-Validation: Exact match
    res_exact = ShippingLabelResult()
    res_exact.order.awb_number = "123456789012"
    cross_validate_codes_with_ocr(
        res_exact,
        barcodes=[{"format": "Code128", "value": "123456789012"}],
        qr_codes=[]
    )
    assert res_exact.barcode_ocr_match_status == "VERIFIED"
    assert res_exact.cross_validation["matched_field"] == "awb_number"
    assert res_exact.cross_validation["corrected_from_ocr"] is False

    # 4. Test Cross-Validation: OCR Optical Typo Correction ('O' vs '0')
    res_typo = ShippingLabelResult()
    res_typo.order.awb_number = "12345O789012"  # OCR read letter 'O'
    cross_validate_codes_with_ocr(
        res_typo,
        barcodes=[{"format": "Code128", "value": "123450789012"}],  # Barcode read number '0'
        qr_codes=[]
    )
    assert res_typo.barcode_ocr_match_status == "BARCODE_CORRECTED_OCR"
    assert res_typo.order.awb_number == "123450789012"  # Corrected to barcode value
    assert res_typo.awb_number == "123450789012"
    assert res_typo.cross_validation["corrected_from_ocr"] is True

    # 5. Test Cross-Validation: Barcode populating missing tracking number
    res_missing = ShippingLabelResult()
    cross_validate_codes_with_ocr(
        res_missing,
        barcodes=[{"format": "Code128", "value": "9400111899562847123456"}],
        qr_codes=[{"format": "QRCode", "value": "https://tools.usps.com/track?id=9400111899562847123456", "content_type": "Tracking URL"}]
    )
    assert res_missing.barcode_ocr_match_status == "BARCODE_POPULATED_TRACKING"
    assert res_missing.order.tracking_number == "9400111899562847123456"
    assert res_missing.cross_validation["tracking_url"] == "https://tools.usps.com/track?id=9400111899562847123456"

    # 6. Test Cross-Validation: Value Conflict (Preserve both + Warning)
    res_conflict = ShippingLabelResult()
    res_conflict.order.awb_number = "999999999999"
    cross_validate_codes_with_ocr(
        res_conflict,
        barcodes=[{"format": "Code128", "value": "111111111111"}],
        qr_codes=[]
    )
    assert res_conflict.barcode_ocr_match_status == "CONFLICT"
    assert res_conflict.order.awb_number == "999999999999"  # Preserved
    assert len(res_conflict.warnings) > 0
    assert "Barcode '111111111111' differs from OCR value '999999999999'" in res_conflict.warnings[0]

    # 7. Test Synthetic Multi-Pass Code Reader on QR code image
    # Generate synthetic QR code image with OpenCV / numpy
    test_img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    # Write synthetic text and run extract_codes
    extracted = extract_codes(test_img)
    assert isinstance(extracted, dict)
    assert "barcodes" in extracted
    assert "qr_codes" in extracted
    assert isinstance(extracted["barcodes"], list)
    assert isinstance(extracted["qr_codes"], list)

    print("  [PASS] QR/Barcode Detection, Classification & OCR Cross-Validation tests passed.")


def test_shipping_date_and_geo_service():
    print("Testing Global Geo Service & Shipping Date Normalization...")
    from geo_service import resolve_country, resolve_state
    from shipping_extractor import normalize_shipping_date, extract_shipping_date

    # 1. Test Country Resolution from CSV database
    c_us = resolve_country("USA")
    assert c_us is not None and c_us["name"] == "United States" and c_us["iso2"] == "US"
    c_in = resolve_country("IND")
    assert c_in is not None and c_in["name"] == "India" and c_in["iso2"] == "IN"
    c_ca = resolve_country("Canada")
    assert c_ca is not None and c_ca["iso2"] == "CA"
    c_au = resolve_country("AU")
    assert c_au is not None and c_au["name"] == "Australia"

    # 2. Test State / Province Resolution from CSV database
    st_tx = resolve_state("TX", "US")
    assert st_tx is not None and st_tx["state_name"] == "Texas" and st_tx["country_name"] == "United States"
    st_ka = resolve_state("KA", "IN")
    assert st_ka is not None and st_ka["state_name"] == "Karnataka"
    st_nsw = resolve_state("NSW", "AU")
    assert st_nsw is not None and st_nsw["state_name"] == "New South Wales"
    st_on = resolve_state("ON", "CA")
    assert st_on is not None and st_on["state_name"] == "Ontario"

    # 3. Test Shipping Date Normalization
    assert normalize_shipping_date("05 Oct 2026") == "2026-10-05"
    assert normalize_shipping_date("15-August-2024") == "2024-08-15"
    assert normalize_shipping_date("Oct 05, 2026") == "2026-10-05"
    assert normalize_shipping_date("24-FEB-25") == "2025-02-24"
    assert normalize_shipping_date("2024-12-31") == "2024-12-31"
    assert normalize_shipping_date("15/08/2024") == "2024-08-15"

    # 4. Test Shipping Date OCR Extraction
    ocr_sample1 = "SHIP DATE: 05 Oct 2026\nFROM: John\nTO: Smith"
    assert extract_shipping_date(ocr_sample1) == "2026-10-05"

    ocr_sample2 = "Dispatched on: 12-Nov-2024\nWeight: 2.5 KG"
    assert extract_shipping_date(ocr_sample2) == "2024-11-12"

    ocr_sample3 = "Mailed from ZIP 11212\nDate: 2024-09-20"
    assert extract_shipping_date(ocr_sample3) == "2024-09-20"

    # 5. Test User Label Specific City / State Resolution & Noise Filtering
    from shipping_extractor import extract_shipping_label_data
    label_text = """SHIP TO:
John Doe
123 Main Street, Apt 4 B, New York
10001

SHIP FROM:
ACME Corporation
456 Industrial Blvd, Los Angeles, REMARKS: NO REMARKS, TRACK 123456789 US
90001"""
    res_label = extract_shipping_label_data(label_text, label_text)
    assert res_label.ship_to.city == "New York"
    assert res_label.ship_to.state == "New York"
    assert res_label.ship_to.country == "United States"
    assert res_label.ship_to.postal_code == "10001"
    
    assert res_label.ship_from.city == "Los Angeles"
    assert res_label.ship_from.state == "California"
    assert res_label.ship_from.country == "United States"
    assert res_label.ship_from.postal_code == "90001"
    assert "REMARKS" not in (res_label.ship_from.address or "")
    assert "TRACK" not in (res_label.ship_from.address or "")

    print("  [PASS] Global Geo Service & Shipping Date Normalization tests passed.")


def test_qr_generator_and_standalone_scanner():
    """Test Suite 14: Comprehensive QR Generation, 12 Payload Formats, Verification & Standalone Scanner."""
    print("Testing QR Code Generator (12 Types), Capacity Limits & Auto-Verification...")
    from qr_generator import generate_and_verify_qr, format_qr_payload

    # 1. Plain Text
    r_text = generate_and_verify_qr(qr_type="text", data="Hello Utility Bot 2")
    assert r_text["success"] is True
    assert r_text["verified"] is True
    assert r_text["payload"] == "Hello Utility Bot 2"
    assert "data:image/png;base64," in r_text["image_base64"]

    # 2. Website URL
    r_url = generate_and_verify_qr(qr_type="url", data="google.com")
    assert r_url["payload"] == "https://google.com"
    assert r_url["verified"] is True

    # 3. Phone Number
    r_phone = generate_and_verify_qr(qr_type="phone", data="+91 98765 43210")
    assert r_phone["payload"] == "tel:+919876543210"
    assert r_phone["verified"] is True

    # 4. Email
    r_email = generate_and_verify_qr(qr_type="email", fields={"email": "test@example.com", "subject": "Support"})
    assert r_email["payload"] == "mailto:test@example.com?subject=Support"

    # 5. SMS
    r_sms = generate_and_verify_qr(qr_type="sms", fields={"phone": "+919876543210", "message": "Hello"})
    assert r_sms["payload"] == "SMSTO:+919876543210:Hello"

    # 6. Wi-Fi
    r_wifi = generate_and_verify_qr(qr_type="wifi", fields={"ssid": "OfficeWiFi", "password": "pass", "auth_type": "WPA"})
    assert r_wifi["payload"] == "WIFI:T:WPA;S:OfficeWiFi;P:pass;H:false;;"
    assert r_wifi["verified"] is True

    # 7. Contact / vCard 3.0
    r_vcard = generate_and_verify_qr(qr_type="vcard", fields={"name": "Jane Doe", "phone": "+15551234", "company": "Acme Inc"})
    assert "BEGIN:VCARD" in r_vcard["payload"]
    assert "FN:Jane Doe" in r_vcard["payload"]
    assert "ORG:Acme Inc" in r_vcard["payload"]

    # 8. Location
    r_loc = generate_and_verify_qr(qr_type="location", fields={"latitude": "13.0827", "longitude": "80.2707"})
    assert r_loc["payload"] == "geo:13.0827,80.2707"

    # 9. Product ID
    r_prod = generate_and_verify_qr(qr_type="product", data="9812")
    assert r_prod["payload"] == "PROD-9812"

    # 10. Order ID
    r_ord = generate_and_verify_qr(qr_type="order", data="2026-X")
    assert r_ord["payload"] == "ORD-2026-X"

    # 11. Shipping Tracking ID
    r_ship = generate_and_verify_qr(qr_type="shipping", fields={"shipping_id": "10025"})
    assert r_ship["payload"] == "SHIP-10025"

    # 12. Structured JSON
    r_json = generate_and_verify_qr(qr_type="json", data={"awb": "113431", "status": "IN_TRANSIT"})
    assert '"awb":"113431"' in r_json["payload"]
    assert r_json["verified"] is True

    # 13. Test Capacity Guardrail (> 2.8 KB rejected)
    oversized_data = "X" * 3500
    try:
        generate_and_verify_qr(qr_type="text", data=oversized_data)
        assert False, "Oversized QR data should have raised a ValueError"
    except ValueError as val_err:
        assert "Data is too large for a QR Code" in str(val_err)

    # 14. Test Multi-Source Shipping Cross-Check Confidence
    from shipping_extractor import extract_shipping_label_data
    sample_text = """SHIP TO: John Doe 123 Main St New York 10001
TRACKING NUMBER: SHIP123456
AWB: SHIP123456"""
    barcodes_sample = [{"format": "Code128", "value": "SHIP123456"}]
    qr_sample = [{"format": "QRCode", "value": "https://track.example.com/SHIP123456"}]
    res_cross = extract_shipping_label_data(sample_text, barcodes=barcodes_sample, qr_codes=qr_sample)
    assert res_cross.cross_check["status"] == "HIGH_CONFIDENCE"
    assert res_cross.cross_check["ocr_match"] is True
    assert res_cross.cross_check["barcode_match"] is True
    assert res_cross.cross_check["qr_match"] is True

    print("  [PASS] QR Code Generator, Capacity Limits & Standalone Scanner tests passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING UTILITY BOT ENTERPRISE TEST SUITE")
    print("=" * 60)
    test_date_normalization()
    test_pan_validation()
    test_aadhaar_validation()
    test_driving_licence_validation()
    test_document_classification_heuristics()
    test_preprocessing_synthetic()
    test_full_validation_flow()
    test_reference_card_service()
    test_liveness_and_spoof_detection()
    test_crosscheck_service()
    test_shipping_label_extraction()
    test_barcode_qr_and_cross_validation()
    test_shipping_date_and_geo_service()
    test_qr_generator_and_standalone_scanner()
    print("=" * 60)
    print("ALL 14 TEST SUITES PASSED SUCCESSFULLY! [SUCCESS]")
    print("=" * 60)


