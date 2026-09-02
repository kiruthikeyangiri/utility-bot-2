"""
document_classifier.py - Heuristic and Rule-based Document Classifier.
Assists the pipeline by detecting signature patterns of Indian ID documents
(Aadhaar Front/Back, PAN Front/Back, Driving Licence Front/Back).
"""

import re
from typing import Tuple, Dict


PATTERNS = {
    "aadhaar": [
        r"unique identification authority of india",
        r"government of india",
        r"aadhaar",
        r"enrollment no",
        r"mera aadhaar",
        r"\b\d{4}\s\d{4}\s\d{4}\b",
        r"\b\d{12}\b",
        r"uidai",
        r"vid\s*:",
        r"dob\s*:",
        r"year of birth",
    ],
    "aadhaar_back": [
        r"address\s*:",
        r"c/o\s*:",
        r"s/o\s*:",
        r"d/o\s*:",
        r"w/o\s*:",
        r"pin\s*code",
        r"pin\s*:\s*\d{6}",
        r"\b\d{6}\b",
        r"help@uidai\.gov\.in",
        r"1947",
        r"www\.uidai\.gov\.in",
        r"unique identification authority of india",
    ],
    "pan": [
        r"income tax department",
        r"permanent account number",
        r"govt of india",
        r"pan card",
        r"\b[a-z]{5}[0-9]{4}[a-z]\b",
        r"father'?s?\s*name",
    ],
    "pan_back": [
        r"if found please return to",
        r"income tax pan services unit",
        r"nsdl",
        r"utiitsl",
        r"protean",
        r"national securities depository",
        r"uti infrastructure technology",
        r"alankit",
        r"karvy",
    ],
    "driving_licence": [
        r"driving licen[cs]e",
        r"indian union driving licen[cs]e",
        r"motor vehicles? department",
        r"transport department",
        r"union of india",
        r"form\s*7",
        r"dl\s*no",
        r"licence to drive",
        r"authorisation to drive",
        r"validity",
        r"non[- ]transport",
        r"\b(tn|dl|mh|ka|kl|up|ap|ts|rj|mp|gj|hr|pb|wb)\d{2}\s*\d{4,14}\b",
    ],
    "driving_licence_back": [
        r"class of vehicle",
        r"\bcov\b",
        r"\blmv\b",
        r"\bmcwg\b",
        r"\btrans\b",
        r"badge\s*no",
        r"organ donor",
        r"endorsements?",
    ]
}


def classify_document_heuristics(ocr_text: str) -> Tuple[str, float, Dict[str, int]]:
    """
    Classifies document type based on keyword frequency and regex matching.
    Supports both Front and Back sides of Indian ID cards.
    
    Returns:
        Tuple of (best_match_type, confidence_score, score_breakdown)
    """
    text_lower = ocr_text.lower()
    scores = {
        "aadhaar": 0,
        "aadhaar_back": 0,
        "pan": 0,
        "pan_back": 0,
        "driving_licence": 0,
        "driving_licence_back": 0,
    }

    for doc_type, patterns in PATTERNS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                scores[doc_type] += matches * 2

    # High-priority exact identifiers
    # 1. PAN Front vs PAN Back
    if re.search(r"\b[a-z]{5}[0-9]{4}[a-z]\b", text_lower):
        scores["pan"] += 6
    if re.search(r"if found please return to|income tax pan services|nsdl|utiitsl|protean", text_lower):
        scores["pan_back"] += 8

    # 2. Aadhaar Front vs Aadhaar Back
    if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text_lower):
        scores["aadhaar"] += 5
    if re.search(r"address\s*:|c/o|s/o|d/o|w/o|help@uidai|1947", text_lower):
        scores["aadhaar_back"] += 6

    # 3. Driving Licence Front vs Back
    if re.search(r"driving licen[cs]e|dl\s*no|indian union driving", text_lower):
        scores["driving_licence"] += 5
    if re.search(r"class of vehicle|\bcov\b|\blmv\b|\bmcwg\b|badge\s*no", text_lower):
        scores["driving_licence_back"] += 6

    total_score = sum(scores.values())
    if total_score == 0:
        return "unsupported", 0.0, scores

    best_match = max(scores, key=scores.get)
    best_score = scores[best_match]
    confidence = min(round(best_score / max(total_score, 1), 2), 1.0)

    # Disambiguate Aadhaar Front vs Back: If 12 digit number AND DOB found, it's Front
    if scores["aadhaar"] >= 5 and "dob" in text_lower:
        best_match = "aadhaar"
    # If "address:" or "c/o" is strong without 12-digit number, it's Aadhaar Back
    elif scores["aadhaar_back"] >= 6 and not re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text_lower):
        best_match = "aadhaar_back"

    # If the score is too low, treat as unsupported
    if best_score < 2:
        return "unsupported", confidence, scores

    return best_match, confidence, scores
