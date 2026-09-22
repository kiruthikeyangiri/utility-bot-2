"""
document_crosscheck_service.py - Multi-Document Cross-Verification & Consistency Service.
Compares extracted fields and biometric portraits across two Indian ID documents (Aadhaar, PAN, Driving Licence).
Performs:
1. Fuzzy Name Matching (handles Indian name ordering, initials, and honorifics).
2. Normalized Date of Birth Cross-Matching (handles varying date formats and Year-Only DOBs).
3. Biometric Face Portrait Cross-Matching (using deep feature cosine similarity).
4. Full Field-by-Field Consistency Matrix & Final Verdict.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, Any, Optional, Tuple, List
from face_matching_service import compare_faces


TITLE_HONORIFICS = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "shri", "shree", "smt", "smt.", 
    "dr", "dr.", "master", "kumar", "kumari", "late", "late."
}


def normalize_name_string(name: Optional[str]) -> List[str]:
    """
    Cleans and tokenizes a name string:
    - Removes punctuation and extra whitespace.
    - Strips common Indian titles/honorifics.
    - Returns sorted list of lowercase meaningful word tokens.
    """
    if not name:
        return []

    # Clean punctuation
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", str(name)).lower().strip()
    raw_tokens = [t for t in cleaned.split() if t]

    # Filter honorifics
    tokens = [t for t in raw_tokens if t not in TITLE_HONORIFICS]
    return tokens if tokens else raw_tokens


def calculate_name_similarity(name1: Optional[str], name2: Optional[str]) -> Tuple[float, str]:
    """
    Calculates fuzzy similarity between two names considering Indian naming patterns
    (e.g., 'S Kiruthikeyan' vs 'Kiruthikeyan S' vs 'Kiruthikeyan Shanmugam').
    
    Returns:
        (similarity_score_percentage, match_type_description)
    """
    if not name1 or not name2:
        return 0.0, "Missing Name in one or both documents"

    tokens1 = normalize_name_string(name1)
    tokens2 = normalize_name_string(name2)

    if not tokens1 or not tokens2:
        return 0.0, "Empty Name"

    str1 = " ".join(tokens1)
    str2 = " ".join(tokens2)

    # 1. Exact string match
    if str1 == str2:
        return 100.0, "Exact Match"

    # 2. Token Set / Permutation Match (e.g. 'Kiruthikeyan S' vs 'S Kiruthikeyan')
    sorted_str1 = " ".join(sorted(tokens1))
    sorted_str2 = " ".join(sorted(tokens2))
    if sorted_str1 == sorted_str2:
        return 98.0, "Name Permutation Match"

    # 3. Initials Expansion Match (e.g. 'S Kiruthikeyan' vs 'Shanmugam Kiruthikeyan')
    if len(tokens1) == len(tokens2):
        matches = 0
        for t1, t2 in zip(tokens1, tokens2):
            if t1 == t2:
                matches += 1
            elif (len(t1) == 1 and t2.startswith(t1)) or (len(t2) == 1 and t1.startswith(t2)):
                matches += 1
        if matches == len(tokens1):
            return 92.0, "Initials Expansion Match"

    # Permuted Initials Match
    s_tokens1 = sorted(tokens1, key=len)
    s_tokens2 = sorted(tokens2, key=len)
    if len(s_tokens1) == len(s_tokens2):
        matches = 0
        for t1, t2 in zip(s_tokens1, s_tokens2):
            if t1 == t2 or (len(t1) == 1 and t2.startswith(t1)) or (len(t2) == 1 and t1.startswith(t2)):
                matches += 1
        if matches == len(s_tokens1):
            return 90.0, "Permuted Initials Match"

    # 4. Subset / Middle Name Omission (e.g. 'Kiruthikeyan Giri Shanmugam' vs 'Kiruthikeyan Giri')
    set1, set2 = set(tokens1), set(tokens2)
    intersect = set1.intersection(set2)
    if len(intersect) >= 2 or (len(intersect) == 1 and len(set1) == 1):
        coverage = len(intersect) / float(max(len(set1), len(set2)))
        score = round(70.0 + coverage * 25.0, 1)
        return score, "Partial / Middle Name Variation"

    # 5. Levenshtein / SequenceMatcher Ratio
    seq_ratio = SequenceMatcher(None, str1, str2).ratio()
    seq_score = round(seq_ratio * 100.0, 1)

    if seq_score >= 80.0:
        return seq_score, "High Typo-Tolerant Match"
    elif seq_score >= 60.0:
        return seq_score, "Moderate Phonetic / Spelling Similarity"
    else:
        return seq_score, "Name Mismatch"


def normalize_date_string(dob_raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Standardizes various Indian date formats into:
    - full_iso: 'YYYY-MM-DD'
    - year: 'YYYY'
    """
    if not dob_raw:
        return None, None

    raw = str(dob_raw).strip()
    
    # Try DD/MM/YYYY or DD-MM-YYYY
    m1 = re.search(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})", raw)
    if m1:
        d, m, y = m1.group(1), m1.group(2), m1.group(3)
        return f"{y}-{int(m):02d}-{int(d):02d}", y

    # Try YYYY-MM-DD or YYYY/MM/DD
    m2 = re.search(r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})", raw)
    if m2:
        y, m, d = m2.group(1), m2.group(2), m2.group(3)
        return f"{y}-{int(m):02d}-{int(d):02d}", y

    # Try Year only (common on old Aadhaar cards)
    m3 = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
    if m3:
        y = m3.group(1)
        return None, y

    return None, None


def calculate_dob_similarity(dob1_raw: Optional[str], dob2_raw: Optional[str]) -> Tuple[float, str, str]:
    """
    Cross-checks Date of Birth between two documents.
    
    Returns:
        (score_percentage, match_status, details)
    """
    if not dob1_raw or not dob2_raw:
        return 0.0, "MISSING", "Date of Birth absent in one or both documents"

    iso1, y1 = normalize_date_string(dob1_raw)
    iso2, y2 = normalize_date_string(dob2_raw)

    if iso1 and iso2 and iso1 == iso2:
        return 100.0, "EXACT_MATCH", f"Exact Date Match ({iso1})"

    if y1 and y2 and y1 == y2:
        if not iso1 or not iso2:
            return 90.0, "YEAR_MATCH", f"Year of Birth Match ({y1}) (Year-only format present)"
        else:
            return 60.0, "YEAR_MATCH_ONLY", f"Same Birth Year ({y1}) but day/month differ ({iso1} vs {iso2})"

    return 0.0, "MISMATCH", f"DOB Mismatch ({dob1_raw} vs {dob2_raw})"


def cross_verify_documents(
    doc1_data: Dict[str, Any],
    doc2_data: Dict[str, Any],
    doc1_portrait: Optional[str] = None,
    doc2_portrait: Optional[str] = None,
    doc1_type: str = "primary_id",
    doc2_type: str = "secondary_id"
) -> Dict[str, Any]:
    """
    Performs complete cross-verification between Document 1 and Document 2.
    
    Returns:
        Structured Cross-Verification Report:
        - overall_consistency_score: float (0.0 to 100.0)
        - consistency_status: 'DOCUMENTS_CONSISTENT' | 'DOCUMENTS_MISMATCH'
        - field_comparisons: Dict with Name, DOB, and Face matching diagnostics
        - summary: str
    """
    # 1. Name Check
    name1 = doc1_data.get("name") or doc1_data.get("holder_name") or doc1_data.get("cardholder_name")
    name2 = doc2_data.get("name") or doc2_data.get("holder_name") or doc2_data.get("cardholder_name")
    name_score, name_match_desc = calculate_name_similarity(name1, name2)
    name_status = "MATCH" if name_score >= 70.0 else "MISMATCH"

    # 2. DOB Check
    dob1 = doc1_data.get("date_of_birth") or doc1_data.get("dob")
    dob2 = doc2_data.get("date_of_birth") or doc2_data.get("dob")
    dob_score, dob_status, dob_desc = calculate_dob_similarity(dob1, dob2)

    # 3. Biometric Face Comparison (if portraits are available)
    face_score = 0.0
    face_status = "NOT_AVAILABLE"
    face_details = "Portrait photo not available on one or both documents"
    face_tier = "WEAK"

    if doc1_portrait and doc2_portrait:
        face_res = compare_faces(doc1_portrait, doc2_portrait)
        face_score = face_res.get("match_score", 0.0)
        face_tier = face_res.get("match_tier", "WEAK")
        face_status = "MATCH" if face_score >= 60.0 else "MISMATCH"
        face_details = face_res.get("explanation", "")

    # 4. Weighted Consistency Score Calculation
    # If face is available: Name (40%), DOB (30%), Face (30%)
    # If face is not available: Name (60%), DOB (40%)
    if doc1_portrait and doc2_portrait:
        consistency_score = (name_score * 0.40) + (dob_score * 0.30) + (face_score * 0.30)
    else:
        consistency_score = (name_score * 0.60) + (dob_score * 0.40)

    consistency_score = round(float(consistency_score), 1)

    is_consistent = (
        consistency_score >= 75.0 and 
        name_status == "MATCH" and 
        dob_status in ["EXACT_MATCH", "YEAR_MATCH"]
    )

    status_str = "DOCUMENTS_CONSISTENT" if is_consistent else "DOCUMENTS_MISMATCH"

    summary = (
        f"Cross-Verification {'Passed' if is_consistent else 'Failed'}: "
        f"Overall Consistency {consistency_score}%. "
        f"Name: {name_match_desc} ({name_score}%). "
        f"DOB: {dob_desc}."
    )

    return {
        "overall_consistency_score": consistency_score,
        "consistency_status": status_str,
        "is_consistent": is_consistent,
        "summary": summary,
        "field_comparisons": {
            "name": {
                "doc1_value": name1 or "—",
                "doc2_value": name2 or "—",
                "similarity_score": name_score,
                "status": name_status,
                "details": name_match_desc
            },
            "date_of_birth": {
                "doc1_value": dob1 or "—",
                "doc2_value": dob2 or "—",
                "similarity_score": dob_score,
                "status": dob_status,
                "details": dob_desc
            },
            "portrait_face": {
                "has_portraits": bool(doc1_portrait and doc2_portrait),
                "similarity_score": face_score,
                "match_tier": face_tier,
                "status": face_status,
                "details": face_details
            }
        },
        "doc1_type": doc1_type,
        "doc2_type": doc2_type
    }
