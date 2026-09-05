"""
llm_extractor.py - Hybrid Groq LLM & Pure OCR Rule-Based Document Extraction Engine.
Supports high-speed local rule-based extraction (zero API key needed) and optional
Groq LLM enhancement for complex layout parsing.
"""

import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()

# Try injecting system truststore on Python 3.10+ (vital on Windows)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

import httpx

# System prompt for strict extraction
SYSTEM_PROMPT = """You are an expert Indian Identity Document Information Extraction engine.

You receive OCR text and spatial layout information extracted from an Indian identity document.

Supported Document Types and Sides:
1. "aadhaar" (Front side of Aadhaar card)
2. "aadhaar_back" (Back side of Aadhaar card with Address, C/O, Pincode)
3. "pan" (Front side of PAN card with Name, Father's Name, DOB, PAN number)
4. "pan_back" (Back side of PAN card - barcode / disclaimer only)
5. "driving_licence" (Front side of Driving Licence)
6. "driving_licence_back" (Back side of Driving Licence with vehicle classes & address)

Rules:
1. Determine the exact document type and side.
2. Extract only information clearly present in the OCR text.
3. Never invent or guess missing information.
4. If a field is missing or unreadable, return null.
5. Return only valid JSON adhering strictly to the schema below.

Document Schema Requirements:

--- If Aadhaar Front ("aadhaar"):
{
  "document_type": "aadhaar",
  "name": "<Full Name or null>",
  "date_of_birth": "<DD/MM/YYYY or YYYY-MM-DD or null>",
  "year_of_birth": "<YYYY or null>",
  "gender": "<Male / Female / Transgender or null>",
  "aadhaar_number": "<12-digit number or null>",
  "address": "<Full address if present on front or null>"
}

--- If Aadhaar Back ("aadhaar_back"):
{
  "document_type": "aadhaar_back",
  "care_of": "<C/O, S/O, D/O, W/O Guardian/Spouse Name or null>",
  "address": "<Complete full residential address string>",
  "pincode": "<6-digit postal code or null>",
  "state": "<State name or null>",
  "requires_front_side": true
}

--- If PAN Front ("pan"):
{
  "document_type": "pan",
  "name": "<Full Name of cardholder>",
  "father_name": "<Father's Name>",
  "date_of_birth": "<DD/MM/YYYY or YYYY-MM-DD or null>",
  "pan_number": "<10-character PAN number e.g. ABCDE1234F or null>"
}

--- If PAN Back ("pan_back"):
{
  "document_type": "pan_back",
  "message": "PAN Card Back Side contains no personal details. Please flip the card and upload the FRONT side.",
  "requires_front_side": true
}

--- If Driving Licence Front ("driving_licence"):
{
  "document_type": "driving_licence",
  "name": "<Full Name or null>",
  "date_of_birth": "<DD/MM/YYYY or YYYY-MM-DD or null>",
  "dl_number": "<Driving licence number or null>",
  "address": "<Address or null>",
  "issue_date": "<Date of issue or null>",
  "valid_until": "<Validity date or null>"
}

--- If Driving Licence Back ("driving_licence_back"):
{
  "document_type": "driving_licence_back",
  "vehicle_classes": ["<LMV, MCWG, TRANS, etc.>"],
  "address": "<Address if present or null>",
  "badge_number": "<Badge number or null>",
  "requires_front_side": true
}

--- If any other document, receipt, bill, or unrecognized text:
{
  "document_type": "unsupported",
  "error": "Only Aadhaar Card, PAN Card and Driving Licence are supported."
}
"""


def extract_document_info_pure_ocr(
    ocr_raw_text: str,
    ocr_layout_text: str,
    heuristic_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pure local OCR rule-based extractor using regex and spatial layout patterns.
    Functions 100% offline without needing any LLM or external API keys.
    """
    text = ocr_raw_text or ""
    text_clean = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 1. Classify document type from heuristic hint or text signatures
    raw_type = (heuristic_type or "").lower()
    text_lower = text.lower()

    if "aadhaar" in raw_type:
        doc_type = "aadhaar_back" if "back" in raw_type else "aadhaar"
    elif "pan" in raw_type:
        doc_type = "pan_back" if "back" in raw_type else "pan"
    elif "driving" in raw_type or "dl" in raw_type:
        doc_type = "driving_licence_back" if "back" in raw_type else "driving_licence"
    else:
        doc_type = "unsupported"

    if doc_type == "unsupported":
        if re.search(r"income\s*tax|permanent\s*account|\b[a-z]{5}[0-9]{4}[a-z]\b", text_lower):
            doc_type = "pan_back" if re.search(r"if found please return|nsdl|utiitsl", text_lower) else "pan"
        elif re.search(r"unique\s*identification|aadhaar|uidai|\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b", text_lower):
            doc_type = "aadhaar_back" if (re.search(r"address\s*:|c/o|s/o|d/o|w/o", text_lower) and not re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text_lower)) else "aadhaar"
        elif re.search(r"driving\s*licen|form\s*7|dl\s*no|transport\s*dept", text_lower):
            doc_type = "driving_licence_back" if re.search(r"class of vehicle|badge no", text_lower) else "driving_licence"

    # ==================== AADHAAR FRONT ====================
    if doc_type == "aadhaar":
        # 1. Aadhaar number (12 digits with or without spaces)
        aadhaar_num = None
        m_num = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text) or re.search(r"\b(\d{12})\b", text)
        if m_num:
            aadhaar_num = m_num.group(1)

        # 2. DOB / YOB
        dob = None
        m_dob = re.search(r"(?:DOB|D0B|Date of Birth|பிறந்த நாள்|பிறந்தநாள்|जन्म तिथि)\s*[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})", text, re.I)
        if m_dob:
            dob = m_dob.group(1)
        else:
            all_dates = re.findall(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b", text)
            m_issue = re.search(r"Issue\s*Date\s*:\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})", text, re.I)
            issue_d = m_issue.group(1) if m_issue else None
            for d in all_dates:
                if d != issue_d:
                    dob = d
                    break

        yob = None
        m_yob = re.search(r"(?:Year of Birth|जन्म का वर्ष|YOB)\s*[:\s]*(\d{4})", text, re.I)
        if m_yob:
            yob = m_yob.group(1)

        # 3. Gender (English, Tamil, Hindi)
        gender = None
        if re.search(r"\b(female|பெண்|महिला)\b", text_lower):
            gender = "Female"
        elif re.search(r"\b(male|ஆண்|पुरुष)\b", text_lower):
            gender = "Male"
        elif re.search(r"\b(transgender)\b", text_lower):
            gender = "Transgender"

        # 4. Name extraction
        cleaned_for_name = text
        cleaned_for_name = re.sub(r"Issue\s*Date\s*:\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}", "", cleaned_for_name, flags=re.I)
        cleaned_for_name = re.sub(r"(?:DOB|D0B|Date of Birth|பிறந்த நாள்|பிறந்தநாள்|जन्म तिथि)\s*[:\s]*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}", "", cleaned_for_name, flags=re.I)
        cleaned_for_name = re.sub(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b", "", cleaned_for_name)
        cleaned_for_name = re.sub(r"\b\d+\b", "", cleaned_for_name)
        cleaned_for_name = re.sub(r"\b(Male|Female|Transgender|ஆண்|பெண்|पुरुष|महिला)\b", "", cleaned_for_name, flags=re.I)
        cleaned_for_name = re.sub(r"Government\s*of\s*India|Unique\s*Identification\s*Authority\s*of\s*India|UIDAI|Mera\s*Aadhaar|Aadhaar", "", cleaned_for_name, flags=re.I)

        name = None
        name_patterns = [
            r"\b([A-Z]\.?\s+[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+)*)\b",  # e.g. S Kiruthikeyan
            r"\b([A-Z][a-zA-Z]{2,}\s+[A-Z]\.?)\b",                        # e.g. Kiruthikeyan S
            r"\b([A-Z][a-zA-Z]{2,}\s+[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+)*)\b"  # e.g. Suresh Kumar
        ]
        for pat in name_patterns:
            m_name = re.search(pat, cleaned_for_name)
            if m_name:
                cand = m_name.group(1).strip()
                if not any(j in cand.lower() for j in ["help", "india", "government", "state", "card", "valid", "enrolment"]):
                    name = cand
                    break

        if not name:
            junk_words = ["government", "india", "unique", "authority", "aadhaar", "uidai", "mera", "male", "female", "dob", "birth", "enrollment"]
            for line in lines:
                line_l = line.lower()
                if not any(j in line_l for j in junk_words) and not re.search(r"\d", line):
                    clean_line = re.sub(r"[^a-zA-Z\s\.]", "", line).strip()
                    if len(clean_line) > 2 and len(clean_line.split()) <= 4:
                        name = clean_line
                        break

        return {
            "document_type": "aadhaar",
            "name": name,
            "date_of_birth": dob,
            "year_of_birth": yob,
            "gender": gender,
            "aadhaar_number": aadhaar_num,
            "address": None
        }

    # ==================== AADHAAR BACK ====================
    elif doc_type == "aadhaar_back":
        pincode = None
        m_pin = re.search(r"\b([1-9][0-9]{5})\b", text)
        if m_pin:
            pincode = m_pin.group(1)

        care_of = None
        m_co = re.search(r"(?:C/O|S/O|D/O|W/O|Care of)\s*[:\s]*([A-Za-z\s\.]+)(?:,|\n|$)", text, re.I)
        if m_co:
            care_of = m_co.group(1).strip()

        return {
            "document_type": "aadhaar_back",
            "care_of": care_of,
            "address": text[:300].strip(),
            "pincode": pincode,
            "state": None,
            "requires_front_side": True
        }

    # ==================== PAN FRONT ====================
    elif doc_type == "pan":
        pan_num = None
        m_pan = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
        if m_pan:
            pan_num = m_pan.group(1)

        dob = None
        m_dob = re.search(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b", text)
        if m_dob:
            dob = m_dob.group(1)

        name = None
        father_name = None
        for i, line in enumerate(lines):
            line_l = line.lower()
            if re.search(r"father'?s?\s*name|पिता", line_l):
                if i + 1 < len(lines):
                    candidate = re.sub(r"[^a-zA-Z\s\.]", "", lines[i+1]).strip()
                    if candidate and not any(k in candidate.lower() for k in ["dob", "income", "tax", "permanent"]):
                        father_name = candidate
            elif re.search(r"name|नाम", line_l) and not re.search(r"father", line_l):
                if i + 1 < len(lines):
                    candidate = re.sub(r"[^a-zA-Z\s\.]", "", lines[i+1]).strip()
                    if candidate and not any(k in candidate.lower() for k in ["father", "income", "tax", "permanent", "govt"]):
                        name = candidate

        # Fallback name search if labels not directly matched
        if not name:
            for line in lines:
                clean_line = re.sub(r"[^a-zA-Z\s\.]", "", line).strip()
                if (clean_line.isupper() or len(clean_line.split()) >= 2) and len(clean_line) > 3:
                    if not any(k in clean_line.lower() for k in ["income", "tax", "department", "govt", "india", "permanent", "account", "number", "signature"]):
                        name = clean_line
                        break

        return {
            "document_type": "pan",
            "name": name,
            "father_name": father_name,
            "date_of_birth": dob,
            "pan_number": pan_num
        }

    # ==================== PAN BACK ====================
    elif doc_type == "pan_back":
        return {
            "document_type": "pan_back",
            "message": "PAN Card Back Side contains no personal details. Please flip the card and upload the FRONT side.",
            "requires_front_side": True
        }

    # ==================== DRIVING LICENCE FRONT ====================
    elif doc_type == "driving_licence":
        dl_num = None
        m_dl = re.search(r"(?:DL\s*NO\.?|Licence\s*No\.?)\s*[:\s]*([A-Z0-9\-\s\/]+)", text, re.I)
        if m_dl:
            dl_num = m_dl.group(1).strip()
        else:
            m_dl_regex = re.search(r"\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4,14})\b", text)
            if m_dl_regex:
                dl_num = m_dl_regex.group(1)

        dob = None
        m_dob = re.search(r"(?:DOB|Date of Birth)\s*[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})", text, re.I)
        if not m_dob:
            m_dob = re.search(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b", text)
        if m_dob:
            dob = m_dob.group(1)

        valid_until = None
        m_valid = re.search(r"(?:Valid|Validity|Valid Till|NT|TR)\s*[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})", text, re.I)
        if m_valid:
            valid_until = m_valid.group(1)

        name = None
        for i, line in enumerate(lines):
            if re.search(r"name|holder", line.lower()) and i + 1 < len(lines):
                name = re.sub(r"[^a-zA-Z\s\.]", "", lines[i+1]).strip()
                break

        return {
            "document_type": "driving_licence",
            "name": name,
            "date_of_birth": dob,
            "dl_number": dl_num,
            "address": None,
            "issue_date": None,
            "valid_until": valid_until
        }

    # ==================== DRIVING LICENCE BACK ====================
    elif doc_type == "driving_licence_back":
        vehicle_classes = []
        for vc in ["LMV", "MCWG", "TRANS", "3W-CAB", "HMV", "HGMV", "MCWOG"]:
            if vc in text.upper():
                vehicle_classes.append(vc)

        return {
            "document_type": "driving_licence_back",
            "vehicle_classes": vehicle_classes,
            "address": None,
            "badge_number": None,
            "requires_front_side": True
        }

    return {
        "document_type": "unsupported",
        "error": "Document could not be recognized as an Indian ID card (Aadhaar, PAN, or Driving Licence)."
    }


def get_groq_client(api_key: Optional[str] = None) -> Optional[Any]:
    """Initializes and returns a Groq client instance if API key is provided."""
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key or key.strip() == "" or key == "your_groq_api_key_here":
        return None

    try:
        from groq import Groq
        return Groq(api_key=key.strip())
    except Exception:
        try:
            from groq import Groq
            http_client = httpx.Client(verify=False)
            return Groq(api_key=key.strip(), http_client=http_client)
        except Exception:
            return None


def get_available_models(api_key: Optional[str] = None) -> list:
    """Fetches list of available chat models from Groq account if key is configured."""
    fallback_models = [
        "Pure OCR Engine (Local)",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
        "llama-3.1-8b-instant"
    ]
    try:
        client = get_groq_client(api_key)
        if not client:
            return fallback_models
        models = client.models.list()
        chat_models = [
            m.id for m in models.data
            if not m.id.startswith("whisper") and not "prompt-guard" in m.id
        ]
        preferred = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.1-8b-instant"]
        sorted_models = [m for m in preferred if m in chat_models] + [m for m in chat_models if m not in preferred]
        return sorted_models if sorted_models else fallback_models
    except Exception:
        return fallback_models


def extract_document_info(
    ocr_raw_text: str,
    ocr_layout_text: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    heuristic_hint: Optional[str] = None,
    temperature: float = 0.0
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Main extraction function.
    Runs high-speed local pure OCR extraction first (100% offline).
    If Groq LLM API Key is provided, uses LLM for optional enhancement.
    """
    # 1. Always run high-precision 100% offline Pure OCR Rule-Based Extractor
    pure_ocr_result = extract_document_info_pure_ocr(
        ocr_raw_text=ocr_raw_text,
        ocr_layout_text=ocr_layout_text,
        heuristic_type=heuristic_hint
    )

    client = get_groq_client(api_key)

    # 2. If no Groq API Key is available or if pure OCR successfully extracted key fields, return pure OCR result immediately
    if not client:
        return pure_ocr_result, None

    # If pure OCR already found key ID numbers (Aadhaar / PAN / DL), return it directly for instant 0ms response
    doc_type = pure_ocr_result.get("document_type")
    if doc_type == "aadhaar" and pure_ocr_result.get("aadhaar_number"):
        return pure_ocr_result, None
    elif doc_type == "pan" and pure_ocr_result.get("pan_number"):
        return pure_ocr_result, None
    elif doc_type == "driving_licence" and pure_ocr_result.get("dl_number"):
        return pure_ocr_result, None

    # 3. Optional Groq LLM Path for complex layouts when API key is provided
    primary_model = model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    models_to_try = [primary_model, "llama-3.1-8b-instant", "openai/gpt-oss-120b"]
    models_to_try = list(dict.fromkeys(models_to_try))

    hint_text = f"\nContext/Keyword Analysis Hint: {heuristic_hint}\n" if heuristic_hint else ""
    clean_layout = ocr_layout_text[:3000] if len(ocr_layout_text) > 3000 else ocr_layout_text

    user_content = f"""Here is the extracted OCR text from the document:
{hint_text}
--- RAW OCR TEXT ---
{ocr_raw_text[:2000]}

--- SPATIAL LAYOUT INFORMATION ---
{clean_layout}

Analyze the document text, determine if it is Front or Back of Aadhaar, PAN, or Driving Licence, and return structured JSON strictly adhering to the schema.
"""

    for model in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=5.0
            )

            response_text = completion.choices[0].message.content.strip()

            try:
                extracted_json = json.loads(response_text)
                return extracted_json, None
            except json.JSONDecodeError:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    clean_json_str = response_text[start_idx : end_idx + 1]
                    extracted_json = json.loads(clean_json_str)
                    return extracted_json, None

        except Exception as e:
            continue

    # Fallback to pure OCR rule-based result
    return pure_ocr_result, None
