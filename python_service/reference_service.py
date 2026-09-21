"""
reference_service.py - Privacy-Safe Identity Reference Card Service.
Generates unguessable Reference IDs, masks sensitive document numbers,
generates secure QR tokens, and manages reference card records and revocation.
"""

import os
import json
import secrets
import qrcode
import io
import base64
from datetime import datetime
from typing import Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REFERENCES_FILE = os.path.join(DATA_DIR, "references.json")

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(REFERENCES_FILE):
    with open(REFERENCES_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


def mask_aadhaar(number: Optional[str]) -> str:
    """Masks Aadhaar number showing only the last 4 digits (e.g. XXXX XXXX 4582)."""
    if not number:
        return "XXXX XXXX 0000"
    clean = "".join(filter(str.isdigit, str(number)))
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXX XXXX {last4}"
    return "XXXX XXXX 0000"


def mask_pan(number: Optional[str]) -> str:
    """Masks PAN card number showing first/last characters or standard XXXXX1260E format."""
    if not number:
        return "XXXXX0000X"
    clean = str(number).strip().upper().replace(" ", "")
    if len(clean) == 10:
        return f"XXXXX{clean[5:]}"
    elif len(clean) > 4:
        return f"{'X' * (len(clean) - 4)}{clean[-4:]}"
    return "XXXXX0000X"


def mask_driving_licence(number: Optional[str]) -> str:
    """Masks Driving Licence number exposing only the final 4 digits (e.g. XXXXXXXX 7845)."""
    if not number:
        return "XXXXXXXX 0000"
    clean = str(number).strip().upper().replace(" ", "").replace("-", "").replace("/", "")
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXXXXXX {last4}"
    return "XXXXXXXX 0000"


def mask_document_number(doc_type: str, raw_data: Dict[str, Any]) -> str:
    """Selects and applies the appropriate masking function for the document type."""
    doc_type_lower = (doc_type or "").lower()
    
    if "aadhaar" in doc_type_lower:
        raw_num = raw_data.get("aadhaar_number") or raw_data.get("masked_number")
        return mask_aadhaar(raw_num)
    elif "pan" in doc_type_lower:
        raw_num = raw_data.get("pan_number") or raw_data.get("pan")
        return mask_pan(raw_num)
    elif "driving" in doc_type_lower or "dl" in doc_type_lower:
        raw_num = raw_data.get("dl_number") or raw_data.get("licence_number")
        return mask_driving_licence(raw_num)
    
    # Generic fallback
    for k in ["number", "id_number", "card_number"]:
        if k in raw_data and raw_data[k]:
            val = str(raw_data[k])
            return f"{'X' * max(6, len(val) - 4)}{val[-4:]}" if len(val) >= 4 else "XXXXXXXX"
    return "XXXXXXXX"


def generate_reference_id(doc_type: str) -> str:
    """
    Generates an unguessable, secure privacy Reference ID:
    - Aadhaar: AAD-KYC-A8F92X
    - PAN: PAN-KYC-P91X52
    - Driving Licence: DL-KYC-B72K91
    """
    doc_type_lower = (doc_type or "").lower()
    if "aadhaar" in doc_type_lower:
        prefix = "AAD"
    elif "pan" in doc_type_lower:
        prefix = "PAN"
    elif "driving" in doc_type_lower or "dl" in doc_type_lower:
        prefix = "DL"
    else:
        prefix = "DOC"

    # Secure random 6-character alphanumeric token
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" # avoid easily confused chars (I, 1, O, 0)
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{prefix}-KYC-{token}"


def generate_qr_code_base64(reference_id: str, qr_token: str) -> str:
    """
    Generates a secure QR Code encoding ONLY the reference URL/token.
    NEVER encodes sensitive personal data directly in the QR code.
    """
    payload_url = f"/reference/{reference_id}?token={qr_token}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def read_reference_records() -> list:
    """Reads all stored reference cards from local storage."""
    try:
        with open(REFERENCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_reference_records(records: list) -> None:
    """Saves reference cards to local storage."""
    try:
        with open(REFERENCES_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"[ReferenceService] Error writing references: {e}")


def create_identity_reference(
    verification_id: str,
    document_type: str,
    extracted_data: Dict[str, Any],
    portrait_photo: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a privacy-safe Identity Reference Record linked to the internal verification ID.
    Original ID document image, full number, raw OCR text, and private addresses are OMITTED.
    """
    ref_id = generate_reference_id(document_type)
    qr_token = secrets.token_urlsafe(16)
    masked_number = mask_document_number(document_type, extracted_data)
    
    applicant_name = (
        extracted_data.get("name") 
        or extracted_data.get("cardholder_name") 
        or extracted_data.get("holder_name") 
        or "Applicant"
    )

    now = datetime.utcnow().isoformat() + "Z"
    
    # Doc type display name
    doc_display_names = {
        "aadhaar": "Aadhaar",
        "aadhaar_back": "Aadhaar",
        "pan": "PAN",
        "pan_back": "PAN",
        "driving_licence": "Driving Licence",
        "driving_licence_back": "Driving Licence"
    }
    doc_display = doc_display_names.get(document_type, document_type.replace("_", " ").title())

    # Generate QR Code image (base64)
    qr_code_image = generate_qr_code_base64(ref_id, qr_token)

    # Privacy-Safe Public Reference Record
    reference_record = {
        "reference_id": ref_id,
        "verification_id": verification_id,
        "qr_token": qr_token,
        "document_type": document_type,
        "document_type_display": doc_display,
        "name": applicant_name,
        "masked_number": masked_number,
        "photo": portrait_photo,  # Cropped face portrait ONLY, NOT the raw document image
        "verification_status": "DETAILS CONFIRMED",
        "created_at": now,
        "revoked": False,
        "device_id": device_id or "default_client",
        "qr_code_image": qr_code_image
    }

    # 1. Save locally
    records = read_reference_records()
    records.insert(0, reference_record)
    if len(records) > 500:
        records = records[:500]
    write_reference_records(records)

    # 2. Sync to MongoDB Atlas
    try:
        from storage import sync_record_to_mongodb
        sync_record_to_mongodb("identity_references", ref_id, reference_record)
    except Exception as err:
        print(f"[ReferenceService] MongoDB sync notice: {err}")

    return reference_record


def get_reference_by_id(ref_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a reference card by its privacy Reference ID."""
    records = read_reference_records()
    for rec in records:
        if rec.get("reference_id") == ref_id:
            return rec
    return None


def revoke_reference_by_id(ref_id: str) -> bool:
    """Revokes an existing Reference ID so it can no longer be used for verification."""
    records = read_reference_records()
    found = False
    for rec in records:
        if rec.get("reference_id") == ref_id:
            rec["revoked"] = True
            rec["revoked_at"] = datetime.utcnow().isoformat() + "Z"
            rec["verification_status"] = "REVOKED"
            found = True
            break
            
    if found:
        write_reference_records(records)
        try:
            from storage import IS_MONGO_ONLINE, _atlas_request
            if IS_MONGO_ONLINE:
                _atlas_request("updateOne", "identity_references", {
                    "filter": {"reference_id": ref_id},
                    "update": {
                        "$set": {
                            "revoked": True, 
                            "verification_status": "REVOKED",
                            "revoked_at": datetime.utcnow().isoformat() + "Z"
                        }
                    }
                })
        except Exception:
            pass
        return True
    return False
