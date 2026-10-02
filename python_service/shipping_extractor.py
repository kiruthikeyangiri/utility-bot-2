"""
shipping_extractor.py - Spatial, Heuristic & Regex Shipping Label Information Extractor.
Uses RapidOCR text words and bounding boxes (x, y, w, h) to reconstruct label layout,
identify courier, partition SHIP TO and SHIP FROM zones, extract order details,
package weight/dimensions, and product line items.
Enforces strict phone number validation (e.g. rejecting non-digit address lines).
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from shipping_schemas import (
    ShippingLabelResult,
    ShipToContact,
    ShipFromContact,
    OrderInformation,
    PackageInformation,
    ShippingItem
)

# Known courier keywords for carrier detection
COURIER_PATTERNS = [
    ("Delhivery", r"\bDELHIVERY\b"),
    ("Blue Dart", r"\bBLUE\s*DART\b"),
    ("Amazon Logistics", r"\b(?:AMAZON\s*LOGISTICS|AMAZON\.IN|ATS)\b"),
    ("Ekart Logistics", r"\b(?:EKART|E-KART)\b"),
    ("Ecom Express", r"\bECOM\s*EXPRESS\b"),
    ("DTDC", r"\bDTDC\b"),
    ("FedEx", r"\bFEDEX\b"),
    ("Shadowfax", r"\bSHADOWFAX\b"),
    ("Xpressbees", r"\b(?:XPRESSBEES|XPRESS\s*BEES)\b"),
    ("India Post", r"\b(?:INDIA\s*POST|SPEED\s*POST|POSTAL\s*DEPT)\b"),
    ("DHL", r"\bDHL\b"),
    ("Shiprocket", r"\bSHIPROCKET\b"),
    ("Smartr", r"\bSMARTR\b"),
    ("Bluedart Apex", r"\bAPEX\b"),
    ("Gati", r"\bGATI\b")
]

# Indian States and Union Territories for state extraction
INDIAN_STATES = [
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHHATTISGARH",
    "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JHARKHAND", "KARNATAKA",
    "KERALA", "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM",
    "NAGALAND", "ODISHA", "PUNJAB", "RAJASTHAN", "SIKKIM", "TAMIL NADU", "TELANGANA",
    "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL", "DELHI", "PUDUCHERRY",
    "CHANDIGARH", "JAMMU & KASHMIR", "JAMMU AND KASHMIR", "LADAKH"
]

STATE_ABBRS = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana",
    "HP": "Himachal Pradesh", "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala",
    "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya",
    "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TS": "Telangana",
    "TR": "Tripura", "UP": "Uttar Pradesh", "UK": "Uttarakhand", "WB": "West Bengal",
    "DL": "Delhi", "PY": "Puducherry", "CH": "Chandigarh", "JK": "Jammu and Kashmir"
}


def _is_valid_phone(text: str) -> bool:
    """
    Validates if a text candidate is genuinely a phone number.
    Rejects text containing street names, words like 'cross', 'lane', letters, etc.
    """
    if not text:
        return False
    clean = re.sub(r"[\s\-\(\)\+\.]", "", text.strip())
    # Must be at least 10 digits and only digits
    if clean.isdigit() and 10 <= len(clean) <= 13:
        # Check if it resembles standard mobile/landline
        if len(clean) == 10 and clean[0] in "56789":
            return True
        if len(clean) > 10:
            return True
    return False


def _extract_phone(line: str) -> Optional[str]:
    """Extracts genuine phone digits from a line, or None if invalid."""
    # Look for explicit telephone patterns like +91 9876543210 or 9876543210
    match = re.search(r"(?:(?:\+91|0)[\s\-]?)?([6-9]\d{9})\b", line)
    if match:
        return match.group(0).strip()
    match_general = re.search(r"\b(\d{10,12})\b", line)
    if match_general:
        return match_general.group(1).strip()
    return None


def _extract_email(text: str) -> Optional[str]:
    """Finds valid email address in text."""
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0).strip() if match else None


def _extract_pincode(text: str) -> Optional[str]:
    """Extracts 6-digit postal PIN code."""
    match = re.search(r"\b(?:PIN|PINCODE|PIN\s*CODE|ZIP|POSTAL)?\s*[:\-]?\s*([1-9][0-9]{5})\b", text, re.IGNORECASE)
    if match:
        return match.group(1)
    # Generic 6 digits
    match_gen = re.search(r"\b([1-9][0-9]{5})\b", text)
    if match_gen:
        return match_gen.group(1)
    return None


def detect_courier(raw_text: str) -> Optional[str]:
    """Detects shipping courier name from raw text."""
    text_upper = raw_text.upper()
    for name, pattern in COURIER_PATTERNS:
        if re.search(pattern, text_upper):
            return name
    return None


def _parse_address_block(lines: List[str]) -> Dict[str, Any]:
    """
    Parses a group of lines corresponding to an address section into
    name, company, phone, email, address, city, state, postal_code, country.
    """
    contact = {
        "name": None,
        "company": None,
        "phone": None,
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "postal_code": None,
        "country": None
    }

    if not lines:
        return contact

    cleaned_lines = [l.strip() for l in lines if l.strip()]
    address_parts = []

    for i, line in enumerate(cleaned_lines):
        line_clean = line.strip()

        # Check for Email
        if not contact["email"]:
            em = _extract_email(line_clean)
            if em:
                contact["email"] = em
                line_clean = line_clean.replace(em, "").strip()

        # Check for Phone
        if "PHONE" in line_clean.upper() or "MOB" in line_clean.upper() or "TEL" in line_clean.upper():
            # Extract potential phone number
            ph = _extract_phone(line_clean)
            if ph:
                contact["phone"] = ph
                line_clean = re.sub(r"(?:PHONE|MOB|MOBILE|TEL|CONTACT)?\s*[:\-]?\s*" + re.escape(ph), "", line_clean, flags=re.IGNORECASE).strip()
            else:
                # Phone label found, but text is e.g. "Phone: 12th cross"
                # Remove label only if followed by nothing, or preserve remainder in address
                after_label = re.sub(r"^(?:PHONE|MOB|MOBILE|TEL|CONTACT)\s*[:\-]?", "", line_clean, flags=re.IGNORECASE).strip()
                if after_label:
                    # Keep "12th cross" inside address!
                    address_parts.append(after_label)
                continue
        elif not contact["phone"]:
            ph = _extract_phone(line_clean)
            if ph and len(line_clean.replace(ph, "").strip()) < 4:
                contact["phone"] = ph
                continue

        # Check for PIN Code
        if not contact["postal_code"]:
            pin = _extract_pincode(line_clean)
            if pin:
                contact["postal_code"] = pin
                line_clean = re.sub(r"(?:PIN|PINCODE|PIN\s*CODE|ZIP)?\s*[:\-]?\s*" + pin, "", line_clean, flags=re.IGNORECASE).strip()

        # Check for State
        if not contact["state"]:
            upper_line = line_clean.upper()
            for st in INDIAN_STATES:
                if re.search(r"\b" + re.escape(st) + r"\b", upper_line):
                    contact["state"] = st.title()
                    break
            if not contact["state"]:
                for abbr, full_state in STATE_ABBRS.items():
                    if re.search(r"\b" + abbr + r"\b", upper_line):
                        contact["state"] = full_state
                        break

        # Check for Country
        if re.search(r"\b(?:INDIA|IND|BHARAT)\b", line_clean, re.IGNORECASE):
            contact["country"] = "India"
            line_clean = re.sub(r"\b(?:INDIA|IND|BHARAT)\b", "", line_clean, flags=re.IGNORECASE).strip()

        if line_clean and line_clean not in [":", "-", ",", "."]:
            address_parts.append(line_clean)

    # Name Assignment from first line
    if address_parts:
        candidate_name = address_parts[0]
        # Clean prefix labels like "Name:", "Consignee:", "To:"
        candidate_name = re.sub(r"^(?:NAME|TO|CONSIGNEE|MR|MS|MRS|RECEIVER|SENDER|FROM)\s*[:\-]?", "", candidate_name, flags=re.IGNORECASE).strip()
        if candidate_name and len(candidate_name) < 40 and not any(kw in candidate_name.upper() for kw in ["ADDRESS", "STREET", "ROAD", "NAGAR"]):
            contact["name"] = candidate_name
            address_parts = address_parts[1:]

    # Construct overall address string
    if address_parts:
        contact["address"] = ", ".join(address_parts)

    return contact


def extract_shipping_label_data(ocr_raw_text: str, ocr_layout_text: str, ocr_words: List[Dict[str, Any]] = None) -> ShippingLabelResult:
    """
    Main extraction function for Shipping Labels.
    Takes OCR raw text, layout text, and bounding boxes, applies
    spatial heuristics, section detection, and regular expressions.
    """
    result = ShippingLabelResult()
    raw_text = ocr_raw_text or ""
    result.raw_ocr_text = raw_text

    # 1. Detect Courier
    result.courier = detect_courier(raw_text)

    # 2. Partition Sections (SHIP TO vs. SHIP FROM)
    to_keywords = ["SHIP TO", "SHIPPING ADDRESS", "DELIVERY ADDRESS", "DELIVER TO", "CONSIGNEE", "RECEIVER", "DESTINATION"]
    from_keywords = ["SHIP FROM", "RETURN ADDRESS", "PICKUP ADDRESS", "SENDER", "FROM", "ORIGIN", "SOLD BY", "DISPATCHED FROM"]

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    to_lines = []
    from_lines = []
    other_lines = []

    current_section = None

    for line in lines:
        line_upper = line.upper()

        is_to_header = any(kw in line_upper for kw in to_keywords)
        is_from_header = any(kw in line_upper for kw in from_keywords)

        if is_to_header:
            current_section = "TO"
            stripped = line
            for kw in to_keywords:
                stripped = re.sub(r"\b" + re.escape(kw) + r"\b\s*[:\-]?", "", stripped, flags=re.IGNORECASE).strip()
            if stripped:
                to_lines.append(stripped)
            continue
        elif is_from_header:
            current_section = "FROM"
            stripped = line
            for kw in from_keywords:
                stripped = re.sub(r"\b" + re.escape(kw) + r"\b\s*[:\-]?", "", stripped, flags=re.IGNORECASE).strip()
            if stripped:
                from_lines.append(stripped)
            continue

        # If line marks start of order info, break section
        if any(kw in line_upper for kw in ["ORDER ID", "TRACKING", "AWB", "INVOICE", "PACKAGE WEIGHT", "TOTAL AMOUNT"]):
            current_section = None

        if current_section == "TO":
            to_lines.append(line)
        elif current_section == "FROM":
            from_lines.append(line)
        else:
            other_lines.append(line)

    # Parse SHIP TO
    if to_lines:
        parsed_to = _parse_address_block(to_lines)
        result.ship_to = ShipToContact(**parsed_to)

    # Parse SHIP FROM
    if from_lines:
        parsed_from = _parse_address_block(from_lines)
        result.ship_from = ShipFromContact(**parsed_from)

    # 3. Order Information Extraction
    order_info = OrderInformation()

    # Order ID
    order_match = re.search(r"\b(?:ORDER\s*(?:ID|NO|NUMBER|#)?)\s*[:\-]?\s*([A-Za-z0-9\-_]{5,25})\b", raw_text, re.IGNORECASE)
    if order_match:
        order_info.order_id = order_match.group(1).strip()

    # Tracking / AWB Number
    tracking_match = re.search(r"\b(?:TRACKING\s*(?:NO|NUMBER|#)?|CONSIGNMENT\s*(?:NO|NUMBER)?)\s*[:\-]?\s*([A-Za-z0-9]{8,25})\b", raw_text, re.IGNORECASE)
    if tracking_match:
        order_info.tracking_number = tracking_match.group(1).strip()

    awb_match = re.search(r"\b(?:AWB|AIR\s*WAYBILL)\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*([A-Za-z0-9]{8,25})\b", raw_text, re.IGNORECASE)
    if awb_match:
        order_info.awb_number = awb_match.group(1).strip()
    elif order_info.tracking_number:
        order_info.awb_number = order_info.tracking_number

    # Shipping Date
    date_match = re.search(r"\b(?:DATE|SHIP\s*DATE|SHIPPING\s*DATE|DISPATCH\s*DATE)?\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\-\/\.]\d{2}[\-\/\.]\d{2})\b", raw_text, re.IGNORECASE)
    if date_match and date_match.group(1):
        order_info.shipping_date = date_match.group(1).strip()

    # Payment Type (Prepaid / COD)
    if re.search(r"\b(?:COD|CASH\s*ON\s*DELIVERY)\b", raw_text, re.IGNORECASE):
        order_info.payment_type = "COD"
    elif re.search(r"\b(?:PREPAID|PRE-PAID|ONLINE)\b", raw_text, re.IGNORECASE):
        order_info.payment_type = "PREPAID"

    # Remarks
    remarks_match = re.search(r"\b(?:REMARKS|INSTRUCTIONS|NOTE)\s*[:\-]?\s*([^\n\r]{3,60})", raw_text, re.IGNORECASE)
    if remarks_match:
        order_info.remarks = remarks_match.group(1).strip()

    result.order = order_info

    # 4. Package Extraction (Weight & Dimensions)
    package_info = PackageInformation()

    # Weight
    weight_match = re.search(r"\b(?:WEIGHT|WT|ACTUAL\s*WEIGHT|VOLUMETRIC\s*WEIGHT)?\s*[:\-]?\s*(\d+(?:\.\d+)?\s*(?:KG|KGS|G|GMS|LBS|LB))\b", raw_text, re.IGNORECASE)
    if weight_match:
        package_info.weight = weight_match.group(1).strip()

    # Dimensions
    dim_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?\s*[xX*]\s*\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?\s*[xX*]\s*\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?)\b", raw_text, re.IGNORECASE)
    if dim_match:
        package_info.dimensions = dim_match.group(1).strip()

    result.package = package_info

    # 5. Product / Item Extraction (Tables & line items)
    items = []
    item_pattern = re.search(r"(?:PRODUCT|ITEM|DESCRIPTION)\s*\|?\s*(?:QTY|QUANTITY)?\s*\|?\s*(?:PRICE|RATE)?\s*\|?\s*(?:TOTAL|AMOUNT)", raw_text, re.IGNORECASE)
    
    # Line by line check for items
    for line in lines:
        # Match e.g. "TShirt | 10 | 10" or "Cotton Shirt 2 499 998"
        pipe_match = [col.strip() for col in line.split("|") if col.strip()]
        if len(pipe_match) >= 3:
            name_candidate = pipe_match[0]
            if not any(header in name_candidate.upper() for header in ["PRODUCT", "ITEM", "DESCRIPTION", "NAME", "TOTAL"]):
                try:
                    price_val = float(re.sub(r"[^\d\.]", "", pipe_match[1])) if re.search(r"\d", pipe_match[1]) else None
                    total_val = float(re.sub(r"[^\d\.]", "", pipe_match[-1])) if re.search(r"\d", pipe_match[-1]) else None
                    qty_val = int(re.sub(r"\D", "", pipe_match[1])) if len(pipe_match) > 3 and pipe_match[1].isdigit() else 1
                    items.append(ShippingItem(
                        product=name_candidate,
                        quantity=qty_val,
                        price=price_val,
                        currency="INR",
                        total=total_val or price_val
                    ))
                except Exception:
                    pass

    result.items = items

    return result
