"""
validation.py - Post-Extraction Validation, Tamper Detection, and Data Sanitization Layer.
Applies rule-based regex checks, date normalization, Verhoeff Aadhaar verification,
Duplicate/Sample watermark detection, and PII masking for Indian ID documents (Front & Back).
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from schemas import (
    AadhaarData,
    AadhaarBackData,
    PANData,
    PANBackData,
    DrivingLicenceData,
    DrivingLicenceBackData,
    UnsupportedDocumentData,
    FinalExtractionResult
)

# Verhoeff mathematical checksum multiplication and permutation tables for Aadhaar
D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]


def check_verhoeff(num_str: str) -> bool:
    """Validates 12-digit Aadhaar number using the mathematical Verhoeff checksum algorithm."""
    digits = [int(c) for c in re.sub(r"\D", "", str(num_str))]
    if len(digits) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = D_TABLE[c][P_TABLE[i % 8][item]]
    return c == 0


def detect_tamper_or_duplicate(raw_ocr_text: Optional[str]) -> Tuple[bool, str, List[str]]:
    """Detects if an ID is marked with DUPLICATE, SAMPLE, SPECIMEN, or DIGITAL COPY watermarks."""
    warnings = []
    if not raw_ocr_text:
        return False, "VERIFIED", warnings

    duplicate_patterns = [
        r"duplicate\s*digital\s*card\s*copy",
        r"duplicate\s*copy",
        r"duplicate",
        r"sample\s*copy",
        r"sample",
        r"specimen",
        r"dummy\s*card",
        r"test\s*copy",
        r"for\s*testing\s*only",
        r"not\s*valid\s*for\s*official",
        r"mock\s*copy",
        r"replica",
        r"fake\s*card",
    ]
    
    text_lower = raw_ocr_text.lower()
    for pat in duplicate_patterns:
        if re.search(pat, text_lower):
            warnings.append("⚠️ SECURITY ALERT: 'DUPLICATE / SAMPLE COPY' watermark detected! This document is not a genuine government-issued physical card.")
            return True, "DUPLICATE_COPY", warnings

    return False, "VERIFIED", warnings


def normalize_date(raw_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Normalizes various date formats into standard ISO format (YYYY-MM-DD)."""
    if not raw_date or not isinstance(raw_date, str):
        return None, None

    date_str = raw_date.strip()
    if not date_str or date_str.lower() == "null" or date_str.lower() == "none":
        return None, None

    date_patterns = [
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
        ("%d.%m.%Y", r"^\d{1,2}\.\d{1,2}\.\d{4}$"),
        ("%Y-%m-%d", r"^\d{4}-\d{1,2}-\d{1,2}$"),
        ("%Y/%m/%d", r"^\d{4}/\d{1,2}/\d{1,2}$"),
        ("%d %b %Y", r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$"),
        ("%d %B %Y", r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}$"),
    ]

    for fmt, regex in date_patterns:
        if re.match(regex, date_str):
            try:
                parsed = datetime.strptime(date_str, fmt)
                if 1900 <= parsed.year <= datetime.now().year + 50:
                    return parsed.strftime("%Y-%m-%d"), None
                else:
                    return date_str, f"Date year '{parsed.year}' out of reasonable range."
            except ValueError:
                pass

    return date_str, f"Date '{date_str}' could not be normalized to YYYY-MM-DD."


def validate_and_mask_aadhaar(aadhaar_raw: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Validates that Aadhaar has exactly 12 digits, checks Verhoeff integrity, and masks first 8 digits."""
    warnings = []
    if not aadhaar_raw:
        return None, ["Aadhaar number is missing."]

    cleaned = re.sub(r"[\s\-\.]", "", str(aadhaar_raw))

    if re.match(r"^\d{12}$", cleaned):
        # Mathematical Verhoeff validation
        if not check_verhoeff(cleaned):
            warnings.append("⚠️ Aadhaar checksum validation failed (Number does not conform to official UIDAI Verhoeff algorithm).")
        masked = "********" + cleaned[-4:]
        return masked, warnings
    
    if re.match(r"^[\*xX]{8}\d{4}$", cleaned):
        return cleaned, warnings

    warnings.append(f"Aadhaar number '{aadhaar_raw}' does not match standard 12-digit format.")
    return aadhaar_raw, warnings


def validate_pan(pan_raw: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Validates PAN number against standard regex: [A-Z]{5}[0-9]{4}[A-Z]{1}"""
    warnings = []
    if not pan_raw:
        return None, ["PAN number is missing."]

    cleaned = pan_raw.strip().upper().replace(" ", "")

    pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.match(pan_pattern, cleaned):
        warnings.append(f"PAN number '{pan_raw}' does not conform to AAAAA9999A format.")
        return cleaned, warnings

    entity_char = cleaned[3]
    valid_entities = {
        'P': 'Individual', 'C': 'Company', 'H': 'HUF', 'F': 'Firm / LLP',
        'A': 'AOP', 'T': 'Trust', 'B': 'BOI', 'L': 'Local Authority',
        'J': 'Artificial Juridical Person', 'G': 'Government Agency'
    }
    if entity_char not in valid_entities:
        warnings.append(f"⚠️ PAN 4th character '{entity_char}' is non-standard (Fake or invalid entity status).")

    return cleaned, warnings


def validate_driving_licence(dl_raw: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Validates Driving Licence format across Indian states with common OCR typo corrections."""
    warnings = []
    if not dl_raw:
        return None, ["Driving Licence number is missing."]

    cleaned = dl_raw.strip().upper().replace("-", " ").replace("/", " ")
    cleaned_no_space = cleaned.replace(" ", "")

    # Common OCR typo corrections for Indian State Codes
    ocr_state_fixes = {
        "N7": "TN", "7N": "TN", "TM": "TN", "IN": "TN",
        "D1": "DL", "DI": "DL", "OL": "DL",
        "K4": "KA", "KH": "KA",
        "M1": "MH", "M#": "MH", "PH": "MH",
        "U9": "UP", "VR": "UP",
        "A9": "AP", "AB": "AP",
        "G1": "GJ", "6J": "GJ"
    }
    
    prefix = cleaned_no_space[:2]
    if prefix in ocr_state_fixes:
        corrected_prefix = ocr_state_fixes[prefix]
        cleaned_no_space = corrected_prefix + cleaned_no_space[2:]
        dl_raw = corrected_prefix + " " + dl_raw[2:].strip()
        prefix = corrected_prefix

    state_codes = [
        "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
        "HR", "HP", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
        "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"
    ]

    if prefix not in state_codes:
        warnings.append(f"Driving licence state code '{prefix}' may be non-standard.")

    if not (10 <= len(cleaned_no_space) <= 20):
        warnings.append(f"Driving licence length ({len(cleaned_no_space)}) is unusual.")

    return dl_raw.strip(), warnings


def sanitize_gender(gender_raw: Optional[str]) -> Optional[str]:
    """Standardizes gender text to Male/Female/Transgender."""
    if not gender_raw:
        return None
    g = gender_raw.strip().lower()
    if g.startswith("m") or "male" in g:
        return "Male"
    if g.startswith("f") or "female" in g:
        return "Female"
    if "trans" in g:
        return "Transgender"
    return gender_raw.strip().title()


def clean_name(name_raw: Optional[str]) -> Optional[str]:
    """Cleans up names by removing junk characters and normalizing spacing."""
    if not name_raw or not isinstance(name_raw, str):
        return None
    cleaned = re.sub(r"[^a-zA-Z\s\.]", "", name_raw).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned if len(cleaned) > 1 else None


def validate_and_clean_extraction(
    raw_data: Dict[str, Any],
    ocr_confidence: float = 0.0,
    raw_ocr_text: Optional[str] = None,
    quality_report: Optional[Dict[str, Any]] = None,
    images: Optional[Dict[str, str]] = None,
    short_circuited: bool = False
) -> FinalExtractionResult:
    """Main validation pipeline that parses LLM output into typed Pydantic models and checks for duplicates."""
    doc_type = raw_data.get("document_type", "unsupported").lower()
    warnings: List[str] = []

    # Check for Duplicate / Specimen / Sample watermarks
    is_duplicate, auth_status, dup_warnings = detect_tamper_or_duplicate(raw_ocr_text)
    warnings.extend(dup_warnings)

    # 1. AADHAAR FRONT
    if doc_type == "aadhaar":
        raw_num = raw_data.get("aadhaar_number")
        if not raw_num and raw_ocr_text:
            aadhaar_match = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", raw_ocr_text) or re.search(r"\b(\d{12})\b", raw_ocr_text)
            if aadhaar_match:
                raw_num = aadhaar_match.group(1)

        name = clean_name(raw_data.get("name"))
        gender = sanitize_gender(raw_data.get("gender"))
        
        dob, dob_warn = normalize_date(raw_data.get("date_of_birth"))
        if dob_warn:
            warnings.append(dob_warn)

        yob = raw_data.get("year_of_birth")
        if yob and not re.match(r"^\d{4}$", str(yob)):
            warnings.append(f"Invalid year of birth: '{yob}'")
            yob = None

        aadhaar_num, num_warn = validate_and_mask_aadhaar(raw_num)
        warnings.extend(num_warn)

        address = raw_data.get("address")
        if address and isinstance(address, str):
            address = address.strip()

        aadhaar_model = AadhaarData(
            document_type="aadhaar",
            name=name,
            date_of_birth=dob,
            year_of_birth=str(yob) if yob else None,
            gender=gender,
            aadhaar_number=aadhaar_num,
            address=address
        )

        return FinalExtractionResult(
            document_type="aadhaar",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=aadhaar_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 2. AADHAAR BACK (Address Side)
    elif doc_type == "aadhaar_back":
        address = raw_data.get("address")
        if not address and raw_ocr_text:
            addr_idx = raw_ocr_text.lower().find("address")
            if addr_idx != -1:
                address = raw_ocr_text[addr_idx + 8:].strip()

        pincode = raw_data.get("pincode")
        if not pincode and raw_ocr_text:
            pin_match = re.search(r"\b\d{6}\b", raw_ocr_text)
            if pin_match:
                pincode = pin_match.group(0)

        care_of = raw_data.get("care_of")
        state = raw_data.get("state")

        aadhaar_back_model = AadhaarBackData(
            document_type="aadhaar_back",
            care_of=care_of,
            address=address,
            pincode=pincode,
            state=state,
            requires_front_side=True
        )

        warnings.append("Aadhaar Back Side verified (Address extracted). Upload the Front Side to complete Name & DOB verification.")

        return FinalExtractionResult(
            document_type="aadhaar_back",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=aadhaar_back_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 3. PAN FRONT
    elif doc_type == "pan":
        raw_pan = raw_data.get("pan_number")
        if not raw_pan and raw_ocr_text:
            pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", raw_ocr_text.upper())
            if pan_match:
                raw_pan = pan_match.group(1)

        name = clean_name(raw_data.get("name"))
        father_name = clean_name(raw_data.get("father_name"))

        # Function to test if a string is a genuine valid person name (not OCR noise like 'wu at')
        def is_valid_name_token(n_str: Optional[str]) -> bool:
            if not n_str or len(n_str.strip()) < 3:
                return False
            n_clean = n_str.strip()
            # Reject lowercase junk or 2-letter noise words like 'wu at', 'met', 'to', 'in'
            tokens = n_clean.split()
            if any(len(t) < 3 and not t.isupper() for t in tokens):
                return False
            # Check noise blacklist
            blacklist = {
                "ram", "nam", "naam", "pita", "father", "fathers", "name", 
                "pita ka naam", "shri", "mr", "met", "minor", "sign", "signature", 
                "govt", "income", "tax", "dept", "india", "permanent", "account", 
                "card", "wu at", "wu", "at", "date", "birth", "hastakshar"
            }
            if n_clean.lower() in blacklist or any(t.lower() in blacklist for t in tokens):
                return False
            return True

        if not is_valid_name_token(father_name) and raw_ocr_text:
            # Deterministic scan in raw OCR text for all-uppercase person name lines
            lines = [l.strip() for l in raw_ocr_text.splitlines() if l.strip()]
            for idx, line in enumerate(lines):
                if re.search(r"father|पिता|name", line, re.IGNORECASE):
                    for next_idx in range(idx + 1, min(idx + 5, len(lines))):
                        candidate = lines[next_idx].strip()
                        # Must not be a date, PAN number, or header keyword
                        if not re.search(r"\d{2}[/-]\d{2}[/-]\d{4}|\b[A-Z]{5}\d{4}[A-Z]\b|income|tax|dept|govt|india|permanent|account|minor|sign|birth|date|signature", candidate, re.IGNORECASE):
                            cleaned_cand = clean_name(candidate)
                            if is_valid_name_token(cleaned_cand) and cleaned_cand != name:
                                father_name = cleaned_cand.upper()
                                break
                    if is_valid_name_token(father_name):
                        break

            # Fallback: scan all lines for any pure uppercase name string (e.g. SEVUGAPERUMAL)
            if not is_valid_name_token(father_name):
                for line in lines:
                    cleaned_line = clean_name(line)
                    if cleaned_line and is_valid_name_token(cleaned_line) and cleaned_line != name:
                        if not re.search(r"INCOME|TAX|GOVT|INDIA|PERMANENT|ACCOUNT|FATHER|SIGNATURE|MINOR", cleaned_line.upper()):
                            father_name = cleaned_line.upper()
                            break

        # Check raw OCR text for exact DOB if LLM misread digits
        dob, dob_warn = normalize_date(raw_data.get("date_of_birth"))
        if raw_ocr_text:
            dob_matches = re.findall(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", raw_ocr_text)
            if dob_matches:
                ocr_dob, _ = normalize_date(dob_matches[0])
                if ocr_dob:
                    dob = ocr_dob

        if dob_warn and not dob:
            warnings.append(dob_warn)

        pan_num, pan_warn = validate_pan(raw_pan)
        warnings.extend(pan_warn)

        pan_model = PANData(
            document_type="pan",
            name=name,
            father_name=father_name,
            date_of_birth=dob,
            pan_number=pan_num
        )

        return FinalExtractionResult(
            document_type="pan",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=pan_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 4. PAN BACK (Barcode/Disclaimer Side)
    elif doc_type == "pan_back":
        pan_back_model = PANBackData(
            document_type="pan_back",
            message="PAN Card Back Side detected. The back contains only barcodes/disclaimers. Please upload the FRONT side with Photo and PAN Number.",
            requires_front_side=True
        )

        warnings.append("PAN Back Side detected. No personal details exist on PAN back. Please flip and upload FRONT side.")

        return FinalExtractionResult(
            document_type="pan_back",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=pan_back_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 5. DRIVING LICENCE FRONT
    elif doc_type == "driving_licence":
        name = clean_name(raw_data.get("name"))
        
        dob, dob_warn = normalize_date(raw_data.get("date_of_birth"))
        if dob_warn:
            warnings.append(dob_warn)

        issue_date, issue_warn = normalize_date(raw_data.get("issue_date"))
        if issue_warn:
            warnings.append(issue_warn)

        valid_until, valid_warn = normalize_date(raw_data.get("valid_until"))
        if valid_warn:
            warnings.append(valid_warn)

        raw_dl = raw_data.get("dl_number")
        if not raw_dl and raw_ocr_text:
            dl_match = re.search(r"\b([A-Z]{2}\d{2}\s*\d{4,14})\b", raw_ocr_text.upper())
            if dl_match:
                raw_dl = dl_match.group(1)

        dl_num, dl_warn = validate_driving_licence(raw_dl)
        warnings.extend(dl_warn)

        address = raw_data.get("address")
        if address and isinstance(address, str):
            address = address.strip()

        dl_model = DrivingLicenceData(
            document_type="driving_licence",
            name=name,
            date_of_birth=dob,
            dl_number=dl_num,
            address=address,
            issue_date=issue_date,
            valid_until=valid_until
        )

        return FinalExtractionResult(
            document_type="driving_licence",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=dl_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 6. DRIVING LICENCE BACK
    elif doc_type == "driving_licence_back":
        v_classes = raw_data.get("vehicle_classes", [])
        if isinstance(v_classes, str):
            v_classes = [v_classes]

        dl_back_model = DrivingLicenceBackData(
            document_type="driving_licence_back",
            vehicle_classes=v_classes,
            address=raw_data.get("address"),
            badge_number=raw_data.get("badge_number"),
            requires_front_side=True
        )

        warnings.append("Driving Licence Back Side verified (Vehicle categories extracted). Upload the Front Side to complete DL Number & Name verification.")

        return FinalExtractionResult(
            document_type="driving_licence_back",
            is_valid=True,
            short_circuited=False,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=dl_back_model,
            warnings=warnings,
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )

    # 7. UNSUPPORTED / NON-ID
    else:
        error_msg = raw_data.get("error", "Only Indian Aadhaar Card, PAN Card and Driving Licence are supported.")
        unsupported_model = UnsupportedDocumentData(
            document_type="unsupported",
            error=error_msg
        )
        return FinalExtractionResult(
            document_type="unsupported",
            is_valid=False,
            short_circuited=short_circuited,
            is_duplicate_or_sample=is_duplicate,
            authenticity_status=auth_status,
            data=unsupported_model,
            warnings=["Document is not recognized as an Aadhaar, PAN, or Driving Licence."],
            ocr_confidence=ocr_confidence,
            raw_ocr_text=raw_ocr_text,
            quality_report=quality_report,
            images=images or {}
        )
