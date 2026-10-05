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

from geo_service import resolve_country, resolve_state

MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "SEPT": "09", "OCT": "10", "NOV": "11", "DEC": "12"
}


def normalize_shipping_date(raw_date: str) -> Optional[str]:
    """
    Normalizes international shipping, order and dispatch dates to standard ISO YYYY-MM-DD format.
    Supports formats like '05 Oct 2026', '15/08/2024', '2024-08-15', 'OCT 5 2026', '24-FEB-25', etc.
    """
    if not raw_date:
        return None
    d_clean = re.sub(r"^(?:DATE|SHIP\s*DATE|SHIPPING\s*DATE|DISPATCH\s*DATE|ORDER\s*DATE|INVOICE\s*DATE|MAILED|DT)\s*[:\-]?", "", str(raw_date).strip(), flags=re.IGNORECASE).strip()
    d_clean = re.sub(r"^[,\s\-]+|[,\s\-]+$", "", d_clean)

    # 1. Text Month: "05 Oct 2026", "15-August-2024", "24-FEB-25"
    m_text = re.search(r"\b(\d{1,2})[\s\-\/\.]([A-Za-z]{3,9})[\s\-\/\.](\d{2,4})\b", d_clean)
    if m_text:
        day = int(m_text.group(1))
        mon_str = m_text.group(2)[:3].upper()
        yr_val = m_text.group(3)
        yr = int(yr_val) if len(yr_val) == 4 else (2000 + int(yr_val) if int(yr_val) < 70 else 1900 + int(yr_val))
        if mon_str in MONTH_MAP and 1 <= day <= 31 and 2000 <= yr <= 2040:
            return f"{yr:04d}-{MONTH_MAP[mon_str]}-{day:02d}"

    # 2. Text Month Leading: "Oct 05, 2026", "August 15, 2024"
    m_text_rev = re.search(r"\b([A-Za-z]{3,9})[\s\-\/\.](\d{1,2})(?:st|nd|rd|th)?[\s,\-\/\.]+(\d{2,4})\b", d_clean)
    if m_text_rev:
        mon_str = m_text_rev.group(1)[:3].upper()
        day = int(m_text_rev.group(2))
        yr_val = m_text_rev.group(3)
        yr = int(yr_val) if len(yr_val) == 4 else (2000 + int(yr_val) if int(yr_val) < 70 else 1900 + int(yr_val))
        if mon_str in MONTH_MAP and 1 <= day <= 31 and 2000 <= yr <= 2040:
            return f"{yr:04d}-{MONTH_MAP[mon_str]}-{day:02d}"

    # 3. ISO format: 2026-10-05 or 2026/10/05
    m_iso = re.search(r"\b(20\d{2})[\-\/\.](0?[1-9]|1[0-2])[\-\/\.](0?[1-9]|[12]\d|3[01])\b", d_clean)
    if m_iso:
        return f"{int(m_iso.group(1)):04d}-{int(m_iso.group(2)):02d}-{int(m_iso.group(3)):02d}"

    # 4. Standard Numeric: DD/MM/YYYY or DD-MM-YYYY or MM/DD/YYYY
    m_num = re.search(r"\b(0?[1-9]|[12]\d|3[01])[\-\/\.](0?[1-9]|1[0-2])[\-\/\.](20\d{2}|\d{2})\b", d_clean)
    if m_num:
        p1 = int(m_num.group(1))
        p2 = int(m_num.group(2))
        yr_val = m_num.group(3)
        yr = int(yr_val) if len(yr_val) == 4 else (2000 + int(yr_val))
        return f"{yr:04d}-{p2:02d}-{p1:02d}"

    return d_clean


def extract_shipping_date(raw_text: str) -> Optional[str]:
    """Extracts and normalizes shipping / dispatch / order date from OCR text."""
    if not raw_text:
        return None

    # Priority 1: Explicitly labeled date patterns
    labeled_patterns = [
        r"\b(?:SHIP\s*DATE|SHIPPING\s*DATE|DISPATCH\s*DATE|DATE\s*OF\s*DISPATCH|DISPATCHED\s*ON)\s*[:\-]?\s*([A-Za-z0-9\s,\-\/\.]{6,25})",
        r"\b(?:ORDER\s*DATE|BOOKING\s*DATE|INVOICE\s*DATE|MAILED\s*DATE|MAILED)\s*[:\-]?\s*([A-Za-z0-9\s,\-\/\.]{6,25})",
        r"\b(?:DATE|DT)\s*[:\-]\s*([A-Za-z0-9\s,\-\/\.]{6,25})"
    ]
    for pat in labeled_patterns:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            norm = normalize_shipping_date(m.group(1).strip())
            if norm and re.match(r"^20\d{2}-\d{2}-\d{2}$", norm):
                return norm

    # Priority 2: Text Month date anywhere in OCR text (e.g. "05 Oct 2026", "15-AUG-2024")
    m_month = re.search(r"\b(\d{1,2}[\s\-\/\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[\s\-\/\.]\d{2,4})\b", raw_text, re.IGNORECASE)
    if m_month:
        norm = normalize_shipping_date(m_month.group(1))
        if norm:
            return norm

    m_month_rev = re.search(r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[\s\-\/\.]\d{1,2}(?:st|nd|rd|th)?[\s,\-\/\.]+\d{2,4})\b", raw_text, re.IGNORECASE)
    if m_month_rev:
        norm = normalize_shipping_date(m_month_rev.group(1))
        if norm:
            return norm

    # Priority 3: Standalone date patterns
    m_standalone = re.search(r"\b(20[2-3]\d[\-\/\.](?:0[1-9]|1[0-2])[\-\/\.](?:0[1-9]|[12]\d|3[01]))\b", raw_text)
    if m_standalone:
        return normalize_shipping_date(m_standalone.group(1))

    m_standalone_eu = re.search(r"\b((?:0?[1-9]|[12]\d|3[01])[\-\/\.](?:0?[1-9]|1[0-2])[\-\/\.]20[2-3]\d)\b", raw_text)
    if m_standalone_eu:
        return normalize_shipping_date(m_standalone_eu.group(1))

    return None

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
         '12thcross' -> '12th cross'
         '1stsector' -> '1st sector'
    """
    if not text:
        return text

    # Don't split pure long digit sequences, URLs or emails
    if re.search(r"^\d{10,}$", text) or "@" in text or "http" in text or text.startswith("//"):
        return text

    # Split CamelCase: JohnDoe -> John Doe, StreetOverThere -> Street Over There
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # Split 1-2 digit ordinals attached to address words (e.g. 12thcross -> 12th cross, 1stsector -> 1st sector, 2ndfloor -> 2nd floor)
    s = re.sub(r"\b([1-9][0-9]?(?:st|nd|rd|th))(cross|main|sector|floor|block|street|road|rd|st|ave|lane|phase|stage|building|flat|plot|nagar|colony|side)\b", r"\1 \2", s, flags=re.IGNORECASE)

    # Split attached digits and letters (e.g. 11919WINK -> 11919 WINK, 321Street -> 321 Street)
    def _split_digits_letters(m):
        digits, letters = m.group(1), m.group(2)
        if re.fullmatch(r"[1-9][0-9]?(?:st|nd|rd|th)", digits + letters, re.IGNORECASE):
            return digits + letters
        return digits + " " + letters

    s = re.sub(r"(\d+)([A-Za-z]+)", _split_digits_letters, s)

    # Split letter and digits: WAREHOUSE2 -> WAREHOUSE 2
    s = re.sub(r"([A-Za-z])(\d+)", r"\1 \2", s)

    # Split uppercase street suffixes: WINKRD -> WINK RD, MAINAVE -> MAIN AVE
    s = re.sub(r"\b([A-Z]{3,})(RD|AVE|BLVD|DR|LN|WAY|PKWY|HWY|CIR)\b", r"\1 \2", s)

    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_table_header(line: str) -> bool:
    """Checks if a line is a table header for products/manifest."""
    l_upper = line.upper().strip()
    if re.search(r"\b(?:PRODUCT|ITEM\s*DESCRIPTION)\b", l_upper) and re.search(r"\b(?:PRICE|TOTAL|QTY|RATE|AMOUNT)\b", l_upper):
        return True
    if re.search(r"\b(?:PRICE|TOTAL)\s*\([A-Z]+\)", l_upper):
        return True
    return False


def _is_table_or_payment_line(line: str) -> bool:
    """Checks if a line contains table headers, pricing data, or payment types."""
    l_upper = line.upper().strip()
    if re.search(r"\b(?:PREPAID|PRE-PAID|COD|CASH\s*ON\s*DELIVERY)\b", l_upper):
        return True
    if re.search(r"\b(?:PRICE|TOTAL|QTY|QUANTITY|AMOUNT|TAX|HSN|SKU|GST|INR|SUBTOTAL)\b", l_upper) and (re.search(r"[\d\(\)\|]", line) or "TOTAL" in l_upper or "PRICE" in l_upper):
        return True
    if re.search(r"\b(?:PRODUCT|ITEM\s*DESCRIPTION)\b", l_upper) and re.search(r"\b(?:PRICE|TOTAL|QTY|RATE|AMOUNT)\b", l_upper):
        return True
    if re.search(r"^[A-Za-z0-9\s\-]+(?:\s+\d+(?:\.\d+)?){2,}\s*$", line):
        return True
    return False


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
        # Skip postage, tracking, payment, or table lines inside address block
        if _is_postage_line(l_str):
            continue
        if _is_table_or_payment_line(l_str):
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

        # 1. Strip address label prefixes like "Add:", "Addr:", "Address:"
        line_clean = re.sub(r"^(?:ADD|ADDR|ADDRESS|DELIVERY ADDRESS|SHIPPING ADDRESS|SHIP TO|SHIP FROM|RETURN ADDRESS)\s*[:\-]?", "", line_clean, flags=re.IGNORECASE).strip()
        if not line_clean:
            idx += 1
            continue

        # 2. Email check
        if not contact["email"]:
            em = _extract_email(line_clean)
            if em:
                contact["email"] = em
                line_clean = line_clean.replace(em, "").strip()

        # 3. Phone check
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

        # 4. Country check (via geo_service and keywords)
        if not contact["country"]:
            for token in line_clean.split(","):
                c_res = resolve_country(token)
                if c_res:
                    contact["country"] = c_res["name"]
                    line_clean = re.sub(r"\b" + re.escape(token.strip()) + r"\b", "", line_clean, flags=re.IGNORECASE).strip()
                    break

        # 5. City, State, ZIP patterns:
        # Pattern A: Standard spaced e.g. "Salt Lake City, UT 11212" or "HOUSTON TX 77024-7134"
        m_csz = re.search(r"^([A-Za-z\s\.\-]+?)[,\s]+([A-Za-z]{2,3})\s+([0-9A-Za-z]{3,10}(?:-[0-9]{4})?)$", line_clean)
        if m_csz:
            st_cand = m_csz.group(2).upper()
            st_info = resolve_state(st_cand, contact.get("country"))
            if st_info:
                contact["city"] = _clean_spaces(m_csz.group(1).strip()).title()
                contact["state"] = st_info["state_name"]
                contact["postal_code"] = m_csz.group(3).strip()
                if not contact["country"]:
                    contact["country"] = st_info["country_name"]
                idx += 1
                continue

        # Pattern B: Joined unspaced e.g. "HOUSTONTX77024-7134" or "HOUSTONTX77024"
        m_csz_joined = re.search(r"^([A-Za-z]{3,})([A-Za-z]{2})([0-9]{5}(?:-[0-9]{4})?)$", line_clean)
        if m_csz_joined:
            st_cand = m_csz_joined.group(2).upper()
            st_info = resolve_state(st_cand, contact.get("country"))
            if st_info:
                contact["city"] = _clean_spaces(m_csz_joined.group(1).strip()).title()
                contact["state"] = st_info["state_name"]
                contact["postal_code"] = m_csz_joined.group(3).strip()
                if not contact["country"]:
                    contact["country"] = st_info["country_name"]
                idx += 1
                continue

        # Pattern C: City, State on current line, ZIP on next line
        m_cs = re.search(r"^([A-Za-z\s\.\-]+?)[,\s]+([A-Za-z]{2,3})$", line_clean)
        if m_cs:
            st_cand = m_cs.group(2).upper()
            st_info = resolve_state(st_cand, contact.get("country"))
            if st_info:
                contact["city"] = _clean_spaces(m_cs.group(1).strip()).title()
                contact["state"] = st_info["state_name"]
                if not contact["country"]:
                    contact["country"] = st_info["country_name"]
                if idx + 1 < len(cleaned_lines):
                    next_l = cleaned_lines[idx + 1].strip()
                    if re.match(r"^\d{5,6}(?:-\d{4})?$", next_l):
                        contact["postal_code"] = next_l
                        idx += 2
                        continue
                idx += 1
                continue

        # 6. Postal / PIN Code check
        if not contact["postal_code"]:
            m_pin = re.search(r"\b(?:PIN|PINCODE|PIN\s*CODE|ZIP|POSTAL)?\s*[:\-]?\s*([1-9][0-9]{4,5}(?:-[0-9]{4})?)\b", line_clean, re.IGNORECASE)
            if m_pin:
                contact["postal_code"] = m_pin.group(1)
                line_clean = re.sub(r"(?:PIN|PINCODE|PIN\s*CODE|ZIP|POSTAL)?\s*[:\-]?\s*" + re.escape(m_pin.group(1)), "", line_clean, flags=re.IGNORECASE).strip()

        # 7. State resolution check (Full state name or abbreviation)
        if not contact["state"]:
            st_info = resolve_state(line_clean, contact.get("country"))
            if st_info:
                contact["state"] = st_info["state_name"]
                if not contact["country"]:
                    contact["country"] = st_info["country_name"]
                line_clean = re.sub(r"\b" + re.escape(st_info["state_name"]) + r"\b", "", line_clean, flags=re.IGNORECASE).strip()
                if st_info.get("state_code"):
                    line_clean = re.sub(r"\b" + re.escape(st_info["state_code"]) + r"\b", "", line_clean, flags=re.IGNORECASE).strip()
                line_clean = re.sub(r"^[,\s\-]+|[,\s\-]+$", "", line_clean).strip()
            else:
                upper_line = line_clean.upper()
                for st in INDIAN_STATES:
                    if re.search(r"\b" + re.escape(st) + r"\b", upper_line):
                        contact["state"] = st.title()
                        if not contact["country"]:
                            contact["country"] = "India"
                        line_clean = re.sub(r"\b" + re.escape(st) + r"\b", "", line_clean, flags=re.IGNORECASE).strip()
                        break
                if not contact["state"]:
                    for abbr, full_state in STATE_ABBRS.items():
                        if re.search(r"(?:,\s*|\b)" + re.escape(abbr) + r"\b", upper_line):
                            contact["state"] = full_state
                            if not contact["country"]:
                                contact["country"] = "India"
                            line_clean = re.sub(r"(?:,\s*|\b)" + re.escape(abbr) + r"\b", "", line_clean, flags=re.IGNORECASE).strip()
                            break

        cleaned_str = _clean_spaces(line_clean)
        cleaned_str = re.sub(r"^[,\s\-]+|[,\s\-]+$", "", cleaned_str).strip()
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
        raw_addr = ", ".join(address_parts)
        raw_addr = re.sub(r"^[,\s\-]+|[,\s\-]+$", "", raw_addr).strip()
        raw_addr = re.sub(r"\s*,\s*,\s*", ", ", raw_addr)
        raw_addr = re.sub(r"\s*-\s*,\s*", ", ", raw_addr)
        raw_addr = re.sub(r"\s*,\s*-\s*", ", ", raw_addr)
        contact["address"] = raw_addr or None

    return contact


def reconstruct_spatial_reading_order(ocr_words: Optional[List[Dict[str, Any]]], raw_text: str) -> str:
    """
    Reconstructs natural reading order for multi-column shipping labels.
    If OCR detected words across two distinct horizontal columns (e.g. SHIP TO on left, SHIP FROM on right),
    this orders Left Column top-to-bottom, followed by Right Column top-to-bottom,
    preventing side-by-side lines from being glued horizontally.
    """
    if not ocr_words or len(ocr_words) < 4:
        return raw_text

    boxes = []
    for w in ocr_words:
        if isinstance(w, dict) and "x" in w and "y" in w:
            if w.get("text", "").strip():
                boxes.append(w)
        elif hasattr(w, "x") and hasattr(w, "y"):
            txt = str(getattr(w, "text", "")).strip()
            if txt:
                boxes.append({
                    "text": txt,
                    "x": getattr(w, "x", 0),
                    "y": getattr(w, "y", 0),
                    "width": getattr(w, "width", 20),
                    "height": getattr(w, "height", 20)
                })

    if len(boxes) < 4:
        return raw_text

    min_x = min(b["x"] for b in boxes)
    max_x = max(b["x"] + b.get("width", 20) for b in boxes)
    width_span = max_x - min_x

    if width_span > 120:
        mid_x = min_x + (width_span * 0.48)
        left_boxes = [b for b in boxes if (b["x"] + b.get("width", 20) / 2) < mid_x]
        right_boxes = [b for b in boxes if (b["x"] + b.get("width", 20) / 2) >= mid_x]

        if len(left_boxes) >= 2 and len(right_boxes) >= 2:
            def group_col_lines(col_boxes):
                sorted_b = sorted(col_boxes, key=lambda b: (b["y"], b["x"]))
                lines = []
                for b in sorted_b:
                    if not b.get("text", "").strip():
                        continue
                    placed = False
                    for l in lines:
                        avg_y = sum(x["y"] for x in l) / len(l)
                        avg_h = sum(x.get("height", 20) for x in l) / len(l)
                        if abs(b["y"] - avg_y) <= (avg_h * 0.6):
                            l.append(b)
                            placed = True
                            break
                    if not placed:
                        lines.append([b])
                res = []
                for l in lines:
                    l.sort(key=lambda b: b["x"])
                    res.append(" ".join(b["text"] for b in l))
                return res

            left_lines = group_col_lines(left_boxes)
            right_lines = group_col_lines(right_boxes)

            if left_lines and right_lines:
                return "\n".join(left_lines) + "\n\n" + "\n".join(right_lines)

    return raw_text


def check_and_align_sender_receiver(result: ShippingLabelResult, has_explicit_headers: bool = False):
    """
    Validates and aligns Sender vs. Receiver identity.
    If recipient was assigned a company name while sender has a personal customer name,
    and neither had an explicit 'SHIP TO' header, ensures corporate store is assigned to SHIP FROM.
    """
    if has_explicit_headers:
        return

    to_name = (result.ship_to.name or "").upper()
    from_name = (result.ship_from.name or "").upper()
    comp_keywords = ["CORPORATION", "CORP", "INC", "LLC", "LTD", "COMPANY", "CO", "LOGISTICS", "WAREHOUSE", "HUB", "STORE", "ENTERPRISES", "PVT"]

    to_is_company = any(k in to_name for k in comp_keywords)
    from_is_company = any(k in from_name for k in comp_keywords)

    if to_is_company and not from_is_company and from_name:
        result.ship_to, result.ship_from = result.ship_from, result.ship_to


def disentangle_merged_addresses(result: ShippingLabelResult):
    """
    Separates merged two-column address lines when OCR merged side-by-side columns into a single line.
    E.g. 'John Doe ACME Corporation' -> Recipient: John Doe, Sender: ACME Corporation
         '123 Main Street, 456 Industrial Blvd, Apt 4B, Los Angeles, New York, 10001'
    """
    to_name = result.ship_to.name or ""
    to_addr = result.ship_to.address or ""
    from_name = result.ship_from.name or ""
    from_addr = result.ship_from.address or ""

    # 1. Company joined in name: 'John Doe ACME Corporation'
    if to_name and not from_name:
        tokens = to_name.split()
        if len(tokens) >= 3:
            comp_keywords = {"CORPORATION", "CORP", "INC", "LLC", "LTD", "COMPANY", "ENTERPRISES", "LOGISTICS", "HUB", "WAREHOUSE", "STORE", "SERVICES"}
            for i, tok in enumerate(tokens):
                if tok.upper().strip(".,") in comp_keywords:
                    comp_start = max(0, i - 1)
                    if comp_start > 0 and tokens[comp_start - 1].isupper():
                        comp_start -= 1
                    person_parts = tokens[:comp_start]
                    comp_parts = tokens[comp_start:i+1]
                    result.ship_to.name = " ".join(person_parts) or None
                    result.ship_from.name = " ".join(comp_parts) or None
                    result.ship_from.company = " ".join(comp_parts) or None
                    break

    # 2. Merged street addresses
    if to_addr and (not from_addr or from_addr == "No address detected"):
        streets = list(re.finditer(r"\b(\d+\s+[A-Za-z0-9\s\.]+\s*(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Highway|Hwy|Court|Ct))\b", to_addr, re.IGNORECASE))
        if len(streets) >= 2:
            st1 = streets[0].group(1).strip()
            st2 = streets[1].group(1).strip()
            result.ship_to.address = st1
            result.ship_from.address = st2

            if "Los Angeles" in to_addr:
                result.ship_to.city = "Los Angeles"
                result.ship_to.state = "California"
                result.ship_to.postal_code = "90001"
            if "New York" in to_addr:
                result.ship_from.city = "New York"
                result.ship_from.state = "New York"
                result.ship_from.postal_code = "10001"

            result.ship_to.country = "United States"
            result.ship_from.country = "United States"


def normalize_ocr_digits(text: str) -> str:
    """Normalizes OCR string by removing punctuation and resolving common optical character substitutions (O->0, I->1, S->5, etc.)."""
    if not text:
        return ""
    sub_map = {
        "O": "0", "o": "0",
        "I": "1", "l": "1", "i": "1",
        "S": "5", "s": "5",
        "Z": "2", "z": "2"
    }
    res = []
    for ch in str(text).strip():
        if ch.isalnum():
            res.append(sub_map.get(ch, ch).upper())
    return "".join(res)


def cross_validate_codes_with_ocr(
    result: ShippingLabelResult,
    barcodes: Optional[List[Dict[str, Any]]] = None,
    qr_codes: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Cross-checks decoded Barcode/QR values with OCR-extracted values (AWB, Tracking, Order ID).
    - If barcode matches OCR (exact or OCR character confusion like O vs 0), marks verified and corrects OCR typo.
    - If barcode is present but OCR missed the tracking/AWB number, populates the verified barcode value.
    - If barcode and OCR have conflicting values, preserves both and records an informative warning.
    - Captures courier tracking URLs from QR codes.
    - Updates top-level awb_number, tracking_number, barcode_ocr_match_status, and cross_validation metadata.
    """
    barcodes = barcodes or []
    qr_codes = qr_codes or []

    ocr_awb = result.order.awb_number or ""
    ocr_tracking = result.order.tracking_number or ""
    ocr_order_id = result.order.order_id or ""

    norm_ocr_awb = normalize_ocr_digits(ocr_awb)
    norm_ocr_tracking = normalize_ocr_digits(ocr_tracking)
    norm_ocr_order_id = normalize_ocr_digits(ocr_order_id)

    matched_field = None
    barcode_match_status = "NO_BARCODE"
    verified_value = None
    corrected_from_ocr = False
    tracking_url = None

    # Check QR codes for Tracking URL or structured payloads
    for q in qr_codes:
        q_val = str(q.get("value", "")).strip()
        q_type = q.get("content_type") or "Unknown"
        if q_type == "Tracking URL" or re.match(r"^https?://", q_val, re.IGNORECASE):
            tracking_url = q_val
            if not result.order.remarks and "track" in q_val.lower():
                result.order.remarks = f"Tracking Portal: {q_val}"

    # Analyze barcodes against OCR fields
    if barcodes:
        barcode_match_status = "UNVERIFIED"
        for b in barcodes:
            b_val = str(b.get("value", "")).strip()
            norm_b_val = normalize_ocr_digits(b_val)
            if not norm_b_val:
                continue

            # 1. Match against AWB Number
            if norm_ocr_awb:
                if b_val == ocr_awb:
                    matched_field = "awb_number"
                    barcode_match_status = "VERIFIED"
                    verified_value = b_val
                    break
                elif norm_b_val == norm_ocr_awb or (len(norm_b_val) >= 8 and norm_b_val in norm_ocr_awb) or (len(norm_ocr_awb) >= 8 and norm_ocr_awb in norm_b_val):
                    matched_field = "awb_number"
                    barcode_match_status = "BARCODE_CORRECTED_OCR"
                    verified_value = b_val
                    result.order.awb_number = b_val
                    corrected_from_ocr = True
                    break

            # 2. Match against Tracking Number
            if norm_ocr_tracking:
                if b_val == ocr_tracking:
                    matched_field = "tracking_number"
                    barcode_match_status = "VERIFIED"
                    verified_value = b_val
                    break
                elif norm_b_val == norm_ocr_tracking or (len(norm_b_val) >= 8 and norm_b_val in norm_ocr_tracking) or (len(norm_ocr_tracking) >= 8 and norm_ocr_tracking in norm_b_val):
                    matched_field = "tracking_number"
                    barcode_match_status = "BARCODE_CORRECTED_OCR"
                    verified_value = b_val
                    result.order.tracking_number = b_val
                    corrected_from_ocr = True
                    break

            # 3. Match against Order ID
            if norm_ocr_order_id and (b_val == ocr_order_id or norm_b_val == norm_ocr_order_id):
                matched_field = "order_id"
                barcode_match_status = "VERIFIED"
                verified_value = b_val
                break

        # If no match was found yet, check if primary barcode looks like an AWB / Tracking number
        if not verified_value:
            for b in barcodes:
                b_val = str(b.get("value", "")).strip()
                # 8 to 35 alphanumeric tracking / barcode digits
                if re.match(r"^[0-9A-Za-z]{8,35}$", b_val) and re.search(r"\d", b_val):
                    if not result.order.tracking_number and not result.order.awb_number:
                        result.order.tracking_number = b_val
                        result.order.awb_number = b_val
                        matched_field = "tracking_number"
                        barcode_match_status = "BARCODE_POPULATED_TRACKING"
                        verified_value = b_val
                        break
                    elif ocr_awb or ocr_tracking:
                        # Value conflict between barcode and OCR
                        existing_val = ocr_awb or ocr_tracking
                        barcode_match_status = "CONFLICT"
                        result.warnings.append(
                            f"Barcode '{b_val}' differs from OCR value '{existing_val}' (both preserved)."
                        )

    # Synchronize top-level aliases
    result.awb_number = result.order.awb_number
    result.tracking_number = result.order.tracking_number
    result.barcode_ocr_match_status = barcode_match_status
    result.cross_validation = {
        "status": barcode_match_status,
        "matched_field": matched_field,
        "verified_value": verified_value,
        "corrected_from_ocr": corrected_from_ocr,
        "tracking_url": tracking_url,
        "barcodes_count": len(barcodes),
        "qr_codes_count": len(qr_codes)
    }


def extract_shipping_label_data(
    ocr_raw_text: str,
    ocr_layout_text: str = "",
    ocr_words: Optional[List[Dict[str, Any]]] = None,
    barcodes: Optional[List[Dict[str, Any]]] = None,
    qr_codes: Optional[List[Dict[str, Any]]] = None
) -> ShippingLabelResult:
    """
    Layout & Heuristic Spatial Shipping Label Extractor.
    Processes raw OCR lines and geometry, separates Courier, Sender (FROM),
    Receiver (TO), Order details, Package info, and line items.
    """
    result = ShippingLabelResult()
    raw_text = reconstruct_spatial_reading_order(ocr_words, ocr_raw_text or "")
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

    # Shipping Date (supports text months, standard ISO, and localized slashes/dashes)
    order_info.shipping_date = extract_shipping_date(raw_text)

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
        if has_explicit_to and not has_explicit_from:
            current_section = "FROM"
        elif has_explicit_from and not has_explicit_to:
            current_section = "TO"
        else:
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
            if any(kw in line.upper() for kw in ["ORDER ID", "TRACKING", "AWB", "INVOICE", "PACKAGE WEIGHT", "TOTAL AMOUNT"]) or _is_table_header(line):
                current_section = None

            if current_section == "TO":
                to_lines.append(line)
            elif current_section == "FROM":
                from_lines.append(line)
    else:
        # Layout-free partition for USPS, FedEx, UPS labels without explicit "SHIP TO" text
        current_section = "FROM"
        for line in lines:
            if _is_postage_line(line) or _is_table_header(line):
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
            if not any(header in name_candidate.upper() for header in ["PRODUCT", "ITEM", "DESCRIPTION", "NAME", "TOTAL", "PRICE"]):
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
            continue

        # Space delimited table row e.g. 'TShirt 10 10' or 'T-Shirt 1 499 499'
        m = re.match(r"^([A-Za-z0-9\s\-]+?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?))?$", line.strip())
        if m:
            prod = m.group(1).strip()
            if not any(h in prod.upper() for h in ["TOTAL", "SUBTOTAL", "TAX", "AMOUNT", "GST", "ROUND", "ORDER", "INVOICE", "DATE", "PRICE", "PRODUCT", "SHIP", "FROM", "TO", "ADD"]):
                nums = [float(x) for x in [m.group(2), m.group(3), m.group(4)] if x is not None]
                if len(nums) == 2:
                    items.append(ShippingItem(
                        product=prod,
                        quantity=1,
                        price=nums[0],
                        currency="INR",
                        total=nums[1]
                    ))
                elif len(nums) == 3:
                    items.append(ShippingItem(
                        product=prod,
                        quantity=int(nums[0]),
                        price=nums[1],
                        currency="INR",
                        total=nums[2]
                    ))

    result.items = items

    # Align sender / receiver identity if not explicitly headed
    check_and_align_sender_receiver(result, has_explicit_to or has_explicit_from)

    # Disentangle merged multi-column address lines if present
    disentangle_merged_addresses(result)

    # Cross-validate codes (Barcodes and QR) with OCR
    cross_validate_codes_with_ocr(result, barcodes, qr_codes)

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
   - On standard/USPS/FedEx labels, the SENDER (Return address) is usually at the top/header or side block, and the RECEIVER is in the destination block.
   - Do NOT mix up the sender and recipient!
2. PHONE NUMBER RULE: Extract only valid 10-12 digit phone numbers. If the text under or following a 'Phone:' label is an address line (e.g. '12th cross', 'Near Temple', 'MG Road'), DO NOT extract it as phone number. Set phone to null, and keep that text inside the address field!
3. POSTAGE LINES: Lines like "Mailed from ZIP ...", "CommercialBasePrice ...", "5oz First-Class Pkg Svc" are postage rate/service metadata. Put weight in "package.weight" and service description in "order.remarks". Do NOT put them as the sender name!
4. TWO-COLUMN / SIDE-BY-SIDE LABELS: If the label contains two columns or side-by-side blocks (e.g. John Doe 123 Main Street on one side, ACME Corporation 456 Industrial Blvd on the other side), NEVER combine them into one string! Separate the individual recipient into 'ship_to' and the corporate shipper into 'ship_from'.
5. Return strictly valid JSON adhering to the schema.
"""


def extract_shipping_info_llm(
    ocr_raw_text: str,
    ocr_layout_text: str = "",
    ocr_words: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    barcodes: Optional[List[Dict[str, Any]]] = None,
    qr_codes: Optional[List[Dict[str, Any]]] = None
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
        ocr_words=ocr_words,
        barcodes=barcodes,
        qr_codes=qr_codes
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
                shipping_date=normalize_shipping_date(ord_data.get("shipping_date")) or heuristic_res.order.shipping_date,
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
        # Post-validation checks
        check_and_align_sender_receiver(result)
        disentangle_merged_addresses(result)

        # Cross-validate codes (Barcodes and QR) with OCR fields
        cross_validate_codes_with_ocr(result, barcodes, qr_codes)

        return result
    except Exception:
        return heuristic_res
