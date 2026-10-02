"""
shipping_extractor.py - Spatial, Heuristic & LLM Shipping Label Information Extractor.
Uses RapidOCR text words and bounding boxes to reconstruct label layout,
identify courier, partition SHIP TO and SHIP FROM zones, extract order details,
package weight/dimensions, and product line items.
Supports domestic and international labels (USPS, FedEx, UPS, Delhivery, Blue Dart, etc.)
and includes Groq LLM intelligence with an automated spatial fallback engine.
"""

import re
import os
import json
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
    ("USPS", r"\b(?:USPS|U\.S\.P\.S\.|POSTAL\s*SERVICE|FIRST-CLASS\s*PKG|PRIORITY\s*MAIL)\b"),
    ("UPS", r"\b(?:UPS|UNITED\s*PARCEL\s*SERVICE)\b"),
    ("FedEx", r"\b(?:FEDEX|FEDERAL\s*EXPRESS)\b"),
    ("Delhivery", r"\bDELHIVERY\b"),
    ("Blue Dart", r"\bBLUE\s*DART\b"),
    ("Amazon Logistics", r"\b(?:AMAZON\s*LOGISTICS|AMAZON\.IN|ATS)\b"),
    ("Ekart Logistics", r"\b(?:EKART|E-KART|FLIPKART)\b"),
    ("Ecom Express", r"\bECOM\s*EXPRESS\b"),
    ("DTDC", r"\bDTDC\b"),
    ("Shadowfax", r"\bSHADOWFAX\b"),
    ("Xpressbees", r"\b(?:XPRESSBEES|XPRESS\s*BEES)\b"),
    ("India Post", r"\b(?:INDIA\s*POST|SPEED\s*POST|POSTAL\s*DEPT)\b"),
    ("DHL", r"\bDHL\b"),
    ("Canada Post", r"\bCANADA\s*POST\b"),
    ("Royal Mail", r"\bROYAL\s*MAIL\b"),
    ("Australia Post", r"\bAUSTRALIA\s*POST\b"),
    ("Shiprocket", r"\bSHIPROCKET\b"),
    ("Smartr", r"\bSMARTR\b"),
    ("Bluedart Apex", r"\bAPEX\b"),
    ("Gati", r"\bGATI\b")
]

# US States mapping
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia"
}

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

POSTAGE_PATTERNS = [
    r"^\d+(?:\.\d+)?\s*(?:oz|lb|lbs|kg|g)\b",
    r"first[- ]class",
    r"priority\s*mail",
    r"commer[a-z0-9]*\s*base",
    r"071s\d+",
    r"usps\s*first",
    r"mailed\s*from\s*zip",
    r"postage\s*and\s*fees",
    r"permit\s*no",
    r"carrier\s*leave\s*if\s*no\s*response",
    r"\b9400\d{15,25}\b",
    r"uspstracking",
]

TO_HEADER_PATTERN = r"^(?:SHIP\s*TO|SHIPPING\s*ADDRESS|DELIVERY\s*ADDRESS|DELIVER\s*TO|CONSIGNEE|RECEIVER|DESTINATION)\b\s*[:\-]?"
FROM_HEADER_PATTERN = r"^(?:SHIP\s*FROM|RETURN\s*ADDRESS|PICKUP\s*ADDRESS|SENDER|ORIGIN|SOLD\s*BY|DISPATCHED\s*FROM|FROM)\b\s*[:\-]?"


def _is_postage_line(line: str) -> bool:
    """Checks if line contains postage, shipping rate or carrier service metadata."""
    l_lower = line.lower().strip()
    return any(bool(re.search(pat, l_lower)) for pat in POSTAGE_PATTERNS)


def _clean_spaces(text: str) -> str:
    """
    Cleans OCR text where words might have been concatenated without spaces.
    E.g. 'JohnDoe' -> 'John Doe'
         'WAREHOUSE2' -> 'WAREHOUSE 2'
         '11919WINKRD' -> '11919 WINK RD'
         '321StreetOverThere' -> '321 Street Over There'
    """
    if not text:
        return text

    # Don't split pure long digit sequences, URLs or emails
    if re.search(r"^\d{10,}$", text) or "@" in text or "http" in text or text.startswith("//"):
        return text

    # Insert space between lower case and Upper case (CamelCase: JohnDoe -> John Doe)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # Insert space between number and letter (except ordinals like 1st, 2nd, 3rd, 4th, etc.)
    # 11919WINK -> 11919 WINK, 321Street -> 321 Street
    # But preserve 1st, 2nd, 3rd, 12th
    s = re.sub(r"(\d+)(?!(?:st|nd|rd|th)\b)([A-Za-z])", r"\1 \2", s, flags=re.IGNORECASE)

    # Insert space between letter and number (except if already separated)
    # WAREHOUSE2 -> WAREHOUSE 2
    s = re.sub(r"([A-Za-z])(\d+)", r"\1 \2", s)

    # Common street suffix splits if joined like WINKRD -> WINK RD, MAINAVE -> MAIN AVE, etc.
    s = re.sub(r"([A-Za-z]{3,})(RD|ST|AVE|BLVD|DR|LN|WAY|PKWY|HWY|CT|CIR)\b", r"\1 \2", s, flags=re.IGNORECASE)

    # Normalize multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
        if len(clean) == 10 and clean[0] in "56789":
            return True
        if len(clean) > 10:
            return True
    return False


def _extract_phone(line: str) -> Optional[str]:
    """Extracts genuine phone digits from a line, or None if invalid."""
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


def detect_courier(raw_text: str) -> Optional[str]:
    """Detects shipping courier name from raw text."""
    text_upper = raw_text.upper()
    for name, pattern in COURIER_PATTERNS:
        if re.search(pattern, text_upper):
            return name
    return None


def _parse_address_block(lines: List[str], is_sender: bool = False) -> Dict[str, Any]:
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

    cleaned_lines = []
    for l in lines:
        l_str = l.strip()
        if not l_str:
            continue
        # Skip postage or tracking lines inside address block
        if _is_postage_line(l_str):
            continue
        if re.search(r"\b(?:USPSTRACKING|TRACKING|BARCODE)\b", l_str, re.IGNORECASE):
            continue
        if re.search(r"^\d{16,}$", l_str):  # Long tracking digits sequence
            continue
        cleaned_lines.append(l_str)

    address_parts = []
    idx = 0
    while idx < len(cleaned_lines):
        line_clean = cleaned_lines[idx].strip()

        # 1. Email check
        if not contact["email"]:
            em = _extract_email(line_clean)
            if em:
                contact["email"] = em
                line_clean = line_clean.replace(em, "").strip()

        # 2. Phone check
        if "PHONE" in line_clean.upper() or "MOB" in line_clean.upper() or "TEL" in line_clean.upper():
            ph = _extract_phone(line_clean)
            if ph:
                contact["phone"] = ph
                line_clean = re.sub(r"(?:PHONE|MOB|MOBILE|TEL|CONTACT)?\s*[:\-]?\s*" + re.escape(ph), "", line_clean, flags=re.IGNORECASE).strip()
            else:
                after_label = re.sub(r"^(?:PHONE|MOB|MOBILE|TEL|CONTACT)\s*[:\-]?", "", line_clean, flags=re.IGNORECASE).strip()
                if after_label:
                    address_parts.append(_clean_spaces(after_label))
                idx += 1
                continue
        elif not contact["phone"]:
            ph = _extract_phone(line_clean)
            if ph and len(line_clean.replace(ph, "").strip()) < 4:
                contact["phone"] = ph
                idx += 1
                continue

        # 3. Country check
        if re.search(r"\b(?:UNITED\s*STATES|USA|U\.S\.A\.|US)\b", line_clean, re.IGNORECASE):
            contact["country"] = "United States"
            line_clean = re.sub(r"\b(?:UNITED\s*STATES|USA|U\.S\.A\.|US)\b", "", line_clean, flags=re.IGNORECASE).strip()
        elif re.search(r"\b(?:INDIA|IND|BHARAT)\b", line_clean, re.IGNORECASE):
            contact["country"] = "India"
            line_clean = re.sub(r"\b(?:INDIA|IND|BHARAT)\b", "", line_clean, flags=re.IGNORECASE).strip()

        # 4. US City, State, ZIP patterns:
        # Pattern A: Standard spaced e.g. "Salt Lake City, UT 11212" or "HOUSTON TX 77024-7134"
        m_csz = re.search(r"^([A-Za-z\s\.\-]+?)[,\s]+([A-Za-z]{2})\s+([0-9]{5}(?:-[0-9]{4})?)$", line_clean)
        if m_csz and m_csz.group(2).upper() in US_STATES:
            contact["city"] = _clean_spaces(m_csz.group(1).strip()).title()
            contact["state"] = US_STATES[m_csz.group(2).upper()]
            contact["postal_code"] = m_csz.group(3).strip()
            if not contact["country"]:
                contact["country"] = "United States"
            idx += 1
            continue

        # Pattern B: Joined unspaced e.g. "HOUSTONTX77024-7134" or "HOUSTONTX77024"
        m_csz_joined = re.search(r"^([A-Za-z]{3,})([A-Za-z]{2})([0-9]{5}(?:-[0-9]{4})?)$", line_clean)
        if m_csz_joined and m_csz_joined.group(2).upper() in US_STATES:
            contact["city"] = _clean_spaces(m_csz_joined.group(1).strip()).title()
            contact["state"] = US_STATES[m_csz_joined.group(2).upper()]
            contact["postal_code"] = m_csz_joined.group(3).strip()
            if not contact["country"]:
                contact["country"] = "United States"
            idx += 1
            continue

        # Pattern C: City, State on current line, ZIP on next line
        # e.g. Current line: "Salt Lake City, UT" or "Salt Lake City UT", Next line: "11212" or "11212-1234"
        m_cs = re.search(r"^([A-Za-z\s\.\-]+?)[,\s]+([A-Za-z]{2})$", line_clean)
        if m_cs and m_cs.group(2).upper() in US_STATES:
            contact["city"] = _clean_spaces(m_cs.group(1).strip()).title()
            contact["state"] = US_STATES[m_cs.group(2).upper()]
            if not contact["country"]:
                contact["country"] = "United States"
            if idx + 1 < len(cleaned_lines):
                next_l = cleaned_lines[idx + 1].strip()
                if re.match(r"^\d{5}(?:-\d{4})?$", next_l):
                    contact["postal_code"] = next_l
                    idx += 2
                    continue
            idx += 1
            continue

        # 5. Postal / PIN Code check
        if not contact["postal_code"]:
            m_pin = re.search(r"\b(?:PIN|PINCODE|PIN\s*CODE|ZIP|POSTAL)?\s*[:\-]?\s*([1-9][0-9]{4,5}(?:-[0-9]{4})?)\b", line_clean, re.IGNORECASE)
            if m_pin:
                contact["postal_code"] = m_pin.group(1)
                line_clean = re.sub(r"(?:PIN|PINCODE|PIN\s*CODE|ZIP|POSTAL)?\s*[:\-]?\s*" + re.escape(m_pin.group(1)), "", line_clean, flags=re.IGNORECASE).strip()

        # 6. Indian State check
        if not contact["state"]:
            upper_line = line_clean.upper()
            for st in INDIAN_STATES:
                if re.search(r"\b" + re.escape(st) + r"\b", upper_line):
                    contact["state"] = st.title()
                    if not contact["country"]:
                        contact["country"] = "India"
                    break
            if not contact["state"]:
                for abbr, full_state in STATE_ABBRS.items():
                    if re.search(r"\b" + abbr + r"\b", upper_line):
                        contact["state"] = full_state
                        if not contact["country"]:
                            contact["country"] = "India"
                        break

        cleaned_str = _clean_spaces(line_clean)
        if cleaned_str and cleaned_str not in [":", "-", ",", "."]:
            address_parts.append(cleaned_str)

        idx += 1

    # Assign Name / Company from top line
    if address_parts:
        candidate_name = address_parts[0]
        candidate_name = re.sub(r"^(?:NAME|TO|CONSIGNEE|MR|MS|MRS|RECEIVER|SENDER|FROM)\s*[:\-]?", "", candidate_name, flags=re.IGNORECASE).strip()
        candidate_name = _clean_spaces(candidate_name)
        street_kws = ["STREET", "RD", "ROAD", "AVE", "BLVD", "LANE", "DRIVE", "WAY", "HWY", "HIGHWAY", "CROSS", "NAGAR", "SECTOR", "PLOT"]
        if len(candidate_name) < 45 and not any(kw in candidate_name.upper() for kw in street_kws):
            contact["name"] = candidate_name
            if any(kw in candidate_name.upper() for kw in ["WAREHOUSE", "LOGISTICS", "STORE", "INC", "CORP", "LTD", "COMPANY", "CO", "FLIPKART", "AMAZON", "ENTERPRISES", "HUB"]):
                contact["company"] = candidate_name
            address_parts = address_parts[1:]

    # Construct overall address string
    if address_parts:
        contact["address"] = ", ".join(address_parts)

    return contact


def extract_shipping_label_data(
    ocr_raw_text: str,
    ocr_layout_text: str = "",
    ocr_words: Optional[List[Dict[str, Any]]] = None
) -> ShippingLabelResult:
    """
    Layout & Heuristic Spatial Shipping Label Extractor.
    Processes raw OCR lines and geometry, separates Courier, Sender (FROM),
    Receiver (TO), Order details, Package info, and line items.
    """
    result = ShippingLabelResult()
    raw_text = ocr_raw_text or ""
    result.raw_ocr_text = raw_text

    # 1. Detect Courier
    result.courier = detect_courier(raw_text)

    # 2. Package Extraction (Weight & Dimensions)
    package_info = PackageInformation()
    weight_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:KG|KGS|G|GMS|LBS|LB|OZ|OUNCES?))\b", raw_text, re.IGNORECASE)
    if weight_match:
        package_info.weight = weight_match.group(1).strip()

    dim_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?\s*[xX*]\s*\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?(?:\s*[xX*]\s*\d+(?:\.\d+)?\s*(?:cm|mm|in|inch|m)?)?)\b", raw_text, re.IGNORECASE)
    if dim_match:
        package_info.dimensions = dim_match.group(1).strip()
    result.package = package_info

    # 3. Order Information Extraction
    order_info = OrderInformation()

    # Order ID (allows short IDs like "286" up to 30 chars)
    order_match = re.search(r"\b(?:ORDER\s*(?:ID|NO|NUMBER|#)?)\s*[:\-]?\s*([A-Za-z0-9\-_]{1,30})\b", raw_text, re.IGNORECASE)
    if order_match:
        order_info.order_id = order_match.group(1).strip()

    # Tracking / AWB Number
    tracking_match = re.search(r"\b(?:TRACKING\s*(?:NO|NUMBER|#)?|CONSIGNMENT\s*(?:NO|NUMBER)?)\s*[:\-]?\s*([A-Za-z0-9]{8,35})\b", raw_text, re.IGNORECASE)
    if tracking_match:
        order_info.tracking_number = tracking_match.group(1).strip()

    awb_match = re.search(r"\b(?:AWB|AIR\s*WAYBILL)\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*([A-Za-z0-9]{8,35})\b", raw_text, re.IGNORECASE)
    if awb_match:
        order_info.awb_number = awb_match.group(1).strip()
    elif order_info.tracking_number:
        order_info.awb_number = order_info.tracking_number

    # Permit / CommercialBase identifier fallback
    permit_match = re.search(r"\b(?:CommercialBasePrice|Permit\s*No\.?)\s*([0-9A-Za-z]{8,25})\b", raw_text, re.IGNORECASE)
    if permit_match:
        if not order_info.tracking_number:
            order_info.tracking_number = permit_match.group(1).strip()
        if not order_info.awb_number:
            order_info.awb_number = permit_match.group(1).strip()

    # Shipping Date
    date_match = re.search(r"\b(?:DATE|SHIP\s*DATE|SHIPPING\s*DATE|DISPATCH\s*DATE)?\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\-\/\.]\d{2}[\-\/\.]\d{2})\b", raw_text, re.IGNORECASE)
    if date_match and date_match.group(1):
        order_info.shipping_date = date_match.group(1).strip()

    # Payment Type
    if re.search(r"\b(?:COD|CASH\s*ON\s*DELIVERY)\b", raw_text, re.IGNORECASE):
        order_info.payment_type = "COD"
    elif re.search(r"\b(?:PREPAID|PRE-PAID|ONLINE)\b", raw_text, re.IGNORECASE):
        order_info.payment_type = "PREPAID"

    # Remarks / Service classification
    remarks_match = re.search(r"\b(?:REMARKS|INSTRUCTIONS|NOTE)\s*[:\-]?\s*([^\n\r]{3,60})", raw_text, re.IGNORECASE)
    if remarks_match:
        order_info.remarks = remarks_match.group(1).strip()
    elif "First-Class" in raw_text:
        order_info.remarks = "First-Class Pkg Svc"
    elif "Priority Mail" in raw_text:
        order_info.remarks = "Priority Mail"

    result.order = order_info

    # 4. Partition Sections (SHIP TO vs. SHIP FROM)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    has_explicit_to = any(bool(re.search(TO_HEADER_PATTERN, l, re.IGNORECASE)) for l in lines)
    has_explicit_from = any(bool(re.search(FROM_HEADER_PATTERN, l, re.IGNORECASE)) and not _is_postage_line(l) for l in lines)

    to_lines: List[str] = []
    from_lines: List[str] = []

    if has_explicit_to or has_explicit_from:
        current_section = None
        for line in lines:
            if re.search(TO_HEADER_PATTERN, line, re.IGNORECASE):
                current_section = "TO"
                s = re.sub(TO_HEADER_PATTERN, "", line, flags=re.IGNORECASE).strip()
                if s: to_lines.append(s)
                continue
            elif re.search(FROM_HEADER_PATTERN, line, re.IGNORECASE) and not _is_postage_line(line):
                current_section = "FROM"
                s = re.sub(FROM_HEADER_PATTERN, "", line, flags=re.IGNORECASE).strip()
                if s: from_lines.append(s)
                continue

            # Section breakers
            if any(kw in line.upper() for kw in ["ORDER ID", "TRACKING", "AWB", "INVOICE", "PACKAGE WEIGHT", "TOTAL AMOUNT"]):
                current_section = None

            if current_section == "TO":
                to_lines.append(line)
            elif current_section == "FROM":
                from_lines.append(line)
    else:
        # Layout-free partition for USPS, FedEx, UPS labels without explicit "SHIP TO" text
        current_section = "FROM"
        for line in lines:
            if _is_postage_line(line):
                continue
            # Order line delimiter switches to recipient
            if re.search(r"\b(?:ORDER\s*(?:ID|NO|NUMBER|#)?)\s*[:\-]?\s*([A-Za-z0-9\-_]{1,30})\b", line, re.IGNORECASE):
                current_section = "TO"
                continue

            if current_section == "FROM":
                from_lines.append(line)
                # If sender line completes a City, State, ZIP code, switch to recipient (TO)
                if re.search(r"[A-Z]{2}\s+[0-9]{5}", line):
                    current_section = "TO"
            else:
                to_lines.append(line)

    # Parse SHIP TO
    if to_lines:
        result.ship_to = ShipToContact(**_parse_address_block(to_lines, is_sender=False))

    # Parse SHIP FROM
    if from_lines:
        result.ship_from = ShipFromContact(**_parse_address_block(from_lines, is_sender=True))

    # 5. Product / Item Extraction (Tables & line items)
    items: List[ShippingItem] = []
    for line in lines:
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


SHIPPING_LLM_SYSTEM_PROMPT = """You are an expert Shipping Label and Logistics Document Extraction AI.
You receive the OCR text and spatial layout information extracted from a parcel/courier shipping label (e.g. USPS, FedEx, UPS, Delhivery, Blue Dart, Amazon, DTDC, etc.).

Your task is to analyze and understand the shipping label layout and text, and accurately separate the data into:
- SENDER / ORIGIN ("ship_from")
- RECEIVER / DESTINATION ("ship_to")
- ORDER & TRACKING ("order")
- PACKAGE WEIGHT & DIMENSIONS ("package")
- PRODUCT LINE ITEMS / MANIFEST ("items")
- COURIER / LOGISTICS CARRIER ("courier")

JSON Schema to return:
{
  "courier": "<Courier Name e.g. USPS, FedEx, UPS, Delhivery, Blue Dart, Ekart, Amazon Logistics, DTDC, DHL, etc., or null>",
  "ship_to": {
    "name": "<Recipient Full Name or null>",
    "phone": "<Recipient Phone Number or null>",
    "email": "<Recipient Email or null>",
    "address": "<Complete Delivery Street Address or null>",
    "city": "<City or null>",
    "state": "<State or null>",
    "postal_code": "<PIN code / ZIP code or null>",
    "country": "<Country e.g. United States, India, or null>"
  },
  "ship_from": {
    "name": "<Sender Contact Name or null>",
    "company": "<Sender Company / Seller / Shipper Store Name or null>",
    "phone": "<Sender Phone Number or null>",
    "email": "<Sender Email or null>",
    "address": "<Complete Sender / Pickup / Return Address or null>",
    "city": "<City or null>",
    "state": "<State or null>",
    "postal_code": "<PIN code / ZIP code or null>",
    "country": "<Country or null>"
  },
  "order": {
    "order_id": "<Order ID or null>",
    "tracking_number": "<Tracking Number or null>",
    "awb_number": "<AWB / Air Waybill Number or null>",
    "shipping_date": "<Shipping or Dispatch Date or null>",
    "payment_type": "<COD / Prepaid / Cash on Delivery or null>",
    "remarks": "<Special instructions, notes, or service rate or null>"
  },
  "package": {
    "weight": "<Package weight e.g. 5oz, 2.5 KG, 1.2 lbs, or null>",
    "dimensions": "<Dimensions e.g. 12x12x12 cm or null>"
  },
  "items": [
    {
      "product": "<Product title or description>",
      "quantity": <integer quantity or null>,
      "price": <unit price as float or null>,
      "currency": "<Currency e.g. USD, INR, etc.>",
      "total": <total price as float or null>
    }
  ]
}

CRITICAL RULES:
1. SENDER vs. RECEIVER:
   - On standard/USPS/FedEx labels, the SENDER (Return address) is usually at the top/header, and the RECEIVER is in the large central block.
   - Do NOT mix up the sender and recipient!
2. PHONE NUMBER RULE: Extract only valid 10-12 digit phone numbers. If the text under or following a 'Phone:' label is an address line (e.g. '12th cross', 'Near Temple', 'MG Road'), DO NOT extract it as phone number. Set phone to null, and keep that text inside the address field!
3. POSTAGE LINES: Lines like "Mailed from ZIP ...", "CommercialBasePrice ...", "5oz First-Class Pkg Svc" are postage rate/service metadata. Put weight in "package.weight" and service description in "order.remarks". Do NOT put them as the sender name!
4. Return strictly valid JSON adhering to the schema.
"""


def extract_shipping_info_llm(
    ocr_raw_text: str,
    ocr_layout_text: str = "",
    ocr_words: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.0
) -> ShippingLabelResult:
    """
    LLM-powered shipping label extraction.
    Sends RapidOCR text and spatial layout to the LLM (Groq / Llama 3.3 / GPT / Qwen).
    The LLM understands the label and separates the data into FROM, TO, Order, Package, Items, etc.
    Falls back to spatial heuristic extraction if LLM is unavailable, offline, or fails.
    """
    from llm_extractor import get_groq_client

    # 1. First run the enhanced baseline heuristic extraction
    heuristic_res = extract_shipping_label_data(
        ocr_raw_text=ocr_raw_text,
        ocr_layout_text=ocr_layout_text,
        ocr_words=ocr_words
    )

    client = get_groq_client(api_key)
    if not client:
        return heuristic_res

    # 2. Build prompt with OCR output
    clean_layout = ocr_layout_text[:3500] if ocr_layout_text else ""
    user_content = f"""Here is the OCR text extracted from the shipping label:

--- RAW OCR TEXT ---
{ocr_raw_text[:3500]}

--- SPATIAL LAYOUT INFORMATION ---
{clean_layout}

Analyze the shipping label text and layout.
Separate all data into SHIP TO (Receiver), SHIP FROM (Sender), ORDER, PACKAGE, and ITEMS.
Return only valid JSON adhering strictly to the schema."""

    primary_model = model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    models_to_try = [primary_model, "llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.1-8b-instant"]
    models_to_try = list(dict.fromkeys(models_to_try))

    extracted_dict = None
    for model in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SHIPPING_LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=8.0
            )
            resp_str = completion.choices[0].message.content.strip()
            try:
                extracted_dict = json.loads(resp_str)
                break
            except json.JSONDecodeError:
                start_i = resp_str.find("{")
                end_i = resp_str.rfind("}")
                if start_i != -1 and end_i != -1:
                    extracted_dict = json.loads(resp_str[start_i:end_i+1])
                    break
        except Exception:
            continue

    if not extracted_dict or not isinstance(extracted_dict, dict):
        return heuristic_res

    # 3. Assemble and validate LLM output into ShippingLabelResult
    try:
        result = ShippingLabelResult()
        result.raw_ocr_text = ocr_raw_text

        # Courier
        llm_courier = extracted_dict.get("courier")
        result.courier = llm_courier or heuristic_res.courier

        # SHIP TO (Receiver)
        to_data = extracted_dict.get("ship_to") or {}
        if isinstance(to_data, dict):
            to_phone = to_data.get("phone")
            to_addr = to_data.get("address")
            if to_phone and not _is_valid_phone(str(to_phone)):
                if to_addr:
                    if str(to_phone) not in to_addr:
                        to_addr = f"{to_phone}, {to_addr}"
                else:
                    to_addr = str(to_phone)
                to_phone = None

            raw_to_name = to_data.get("name") or heuristic_res.ship_to.name
            raw_to_addr = to_addr or heuristic_res.ship_to.address
            raw_to_city = to_data.get("city") or heuristic_res.ship_to.city
            raw_to_state = to_data.get("state") or heuristic_res.ship_to.state
            raw_to_postal = str(to_data.get("postal_code")) if to_data.get("postal_code") is not None else heuristic_res.ship_to.postal_code

            result.ship_to = ShipToContact(
                name=_clean_spaces(raw_to_name) if raw_to_name else None,
                phone=to_phone or (heuristic_res.ship_to.phone if _is_valid_phone(str(heuristic_res.ship_to.phone or "")) else None),
                email=to_data.get("email") or heuristic_res.ship_to.email,
                address=_clean_spaces(raw_to_addr) if raw_to_addr else None,
                city=_clean_spaces(raw_to_city) if raw_to_city else None,
                state=_clean_spaces(raw_to_state) if raw_to_state else None,
                postal_code=raw_to_postal,
                country=to_data.get("country") or heuristic_res.ship_to.country
            )
        else:
            result.ship_to = heuristic_res.ship_to

        # SHIP FROM (Sender)
        from_data = extracted_dict.get("ship_from") or {}
        if isinstance(from_data, dict):
            from_phone = from_data.get("phone")
            from_addr = from_data.get("address")
            if from_phone and not _is_valid_phone(str(from_phone)):
                if from_addr:
                    if str(from_phone) not in from_addr:
                        from_addr = f"{from_phone}, {from_addr}"
                else:
                    from_addr = str(from_phone)
                from_phone = None

            raw_from_name = from_data.get("name") or heuristic_res.ship_from.name
            raw_from_comp = from_data.get("company") or heuristic_res.ship_from.company
            raw_from_addr = from_addr or heuristic_res.ship_from.address
            raw_from_city = from_data.get("city") or heuristic_res.ship_from.city
            raw_from_state = from_data.get("state") or heuristic_res.ship_from.state
            raw_from_postal = str(from_data.get("postal_code")) if from_data.get("postal_code") is not None else heuristic_res.ship_from.postal_code

            # Check if name was accidentally extracted as a postage line
            if raw_from_name and _is_postage_line(raw_from_name):
                raw_from_name = heuristic_res.ship_from.name
            if raw_from_comp and _is_postage_line(raw_from_comp):
                raw_from_comp = heuristic_res.ship_from.company

            result.ship_from = ShipFromContact(
                name=_clean_spaces(raw_from_name) if raw_from_name else None,
                company=_clean_spaces(raw_from_comp) if raw_from_comp else None,
                phone=from_phone or (heuristic_res.ship_from.phone if _is_valid_phone(str(heuristic_res.ship_from.phone or "")) else None),
                email=from_data.get("email") or heuristic_res.ship_from.email,
                address=_clean_spaces(raw_from_addr) if raw_from_addr else None,
                city=_clean_spaces(raw_from_city) if raw_from_city else None,
                state=_clean_spaces(raw_from_state) if raw_from_state else None,
                postal_code=raw_from_postal,
                country=from_data.get("country") or heuristic_res.ship_from.country
            )
        else:
            result.ship_from = heuristic_res.ship_from

        # ORDER
        ord_data = extracted_dict.get("order") or {}
        if isinstance(ord_data, dict):
            result.order = OrderInformation(
                order_id=ord_data.get("order_id") or heuristic_res.order.order_id,
                tracking_number=ord_data.get("tracking_number") or heuristic_res.order.tracking_number,
                awb_number=ord_data.get("awb_number") or heuristic_res.order.awb_number,
                shipping_date=ord_data.get("shipping_date") or heuristic_res.order.shipping_date,
                payment_type=ord_data.get("payment_type") or heuristic_res.order.payment_type,
                remarks=ord_data.get("remarks") or heuristic_res.order.remarks
            )
        else:
            result.order = heuristic_res.order

        # PACKAGE
        pkg_data = extracted_dict.get("package") or {}
        if isinstance(pkg_data, dict):
            result.package = PackageInformation(
                weight=pkg_data.get("weight") or heuristic_res.package.weight,
                dimensions=pkg_data.get("dimensions") or heuristic_res.package.dimensions
            )
        else:
            result.package = heuristic_res.package

        # ITEMS
        items_list = extracted_dict.get("items")
        if isinstance(items_list, list) and items_list:
            parsed_items = []
            for it in items_list:
                if isinstance(it, dict) and it.get("product"):
                    try:
                        q_val = None
                        if it.get("quantity") is not None:
                            q_clean = re.sub(r"[^\d]", "", str(it["quantity"]))
                            q_val = int(q_clean) if q_clean else None

                        p_val = None
                        if it.get("price") is not None:
                            p_clean = re.sub(r"[^\d\.]", "", str(it["price"]))
                            p_val = float(p_clean) if p_clean else None

                        t_val = None
                        if it.get("total") is not None:
                            t_clean = re.sub(r"[^\d\.]", "", str(it["total"]))
                            t_val = float(t_clean) if t_clean else None

                        parsed_items.append(ShippingItem(
                            product=str(it.get("product")),
                            quantity=q_val,
                            price=p_val,
                            currency=str(it.get("currency") or "INR"),
                            total=t_val or p_val
                        ))
                    except Exception:
                        pass
            result.items = parsed_items if parsed_items else heuristic_res.items
        else:
            result.items = heuristic_res.items

        return result
    except Exception:
        return heuristic_res
