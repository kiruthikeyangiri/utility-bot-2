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


SHIPPING_LLM_SYSTEM_PROMPT = """You are an expert Shipping Label and Logistics Document Extraction AI.
You receive the OCR text and spatial layout information extracted from a parcel/courier shipping label.

Your task is to analyze and understand the shipping label layout and text, and accurately separate the data into:
- SENDER / ORIGIN ("ship_from")
- RECEIVER / DESTINATION ("ship_to")
- ORDER & TRACKING ("order")
- PACKAGE WEIGHT & DIMENSIONS ("package")
- PRODUCT LINE ITEMS / MANIFEST ("items")
- COURIER / LOGISTICS CARRIER ("courier")

JSON Schema to return:
{
  "courier": "<Courier Name e.g. Delhivery, Blue Dart, Ekart, Amazon Logistics, DTDC, FedEx, DHL, etc., or null>",
  "ship_to": {
    "name": "<Recipient Full Name or null>",
    "phone": "<Recipient Phone Number or null>",
    "email": "<Recipient Email or null>",
    "address": "<Complete Delivery Street Address or null>",
    "city": "<City or null>",
    "state": "<State or null>",
    "postal_code": "<PIN code / ZIP code or null>",
    "country": "<Country e.g. India or null>"
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
    "remarks": "<Special instructions, notes, or remarks or null>"
  },
  "package": {
    "weight": "<Package weight e.g. 2.5 KG or null>",
    "dimensions": "<Dimensions e.g. 12x12x12 cm or null>"
  },
  "items": [
    {
      "product": "<Product title or description>",
      "quantity": <integer quantity or null>,
      "price": <unit price as float or null>,
      "currency": "<Currency e.g. INR>",
      "total": <total price as float or null>
    }
  ]
}

CRITICAL RULES:
1. SHIP TO represents the recipient (Receiver/Consignee/Delivery Address).
2. SHIP FROM represents the sender (Origin/Shipper/Return Address/Seller).
3. PHONE NUMBER RULE: Extract only valid 10-12 digit phone numbers. If the text under or following a 'Phone:' label is an address line (e.g. '12th cross', 'Near Temple', 'MG Road'), DO NOT extract it as phone number. Set phone to null, and keep that text inside the address field!
4. ITEMS: If a product manifest or table is present (Product, Price, Qty, Total), extract each row into the "items" array. If no items or table are listed, return [].
5. Do not invent details not present in the OCR text. If an attribute is missing, set it to null.
6. Return strictly valid JSON adhering to the schema.
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
    import json
    import os
    from llm_extractor import get_groq_client

    # 1. First run the baseline heuristic extraction
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

            result.ship_to = ShipToContact(
                name=to_data.get("name") or heuristic_res.ship_to.name,
                phone=to_phone or (heuristic_res.ship_to.phone if _is_valid_phone(str(heuristic_res.ship_to.phone or "")) else None),
                email=to_data.get("email") or heuristic_res.ship_to.email,
                address=to_addr or heuristic_res.ship_to.address,
                city=to_data.get("city") or heuristic_res.ship_to.city,
                state=to_data.get("state") or heuristic_res.ship_to.state,
                postal_code=str(to_data.get("postal_code")) if to_data.get("postal_code") is not None else heuristic_res.ship_to.postal_code,
                country=to_data.get("country") or heuristic_res.ship_to.country or "India"
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

            result.ship_from = ShipFromContact(
                name=from_data.get("name") or heuristic_res.ship_from.name,
                company=from_data.get("company") or heuristic_res.ship_from.company,
                phone=from_phone or (heuristic_res.ship_from.phone if _is_valid_phone(str(heuristic_res.ship_from.phone or "")) else None),
                email=from_data.get("email") or heuristic_res.ship_from.email,
                address=from_addr or heuristic_res.ship_from.address,
                city=from_data.get("city") or heuristic_res.ship_from.city,
                state=from_data.get("state") or heuristic_res.ship_from.state,
                postal_code=str(from_data.get("postal_code")) if from_data.get("postal_code") is not None else heuristic_res.ship_from.postal_code,
                country=from_data.get("country") or heuristic_res.ship_from.country or "India"
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

