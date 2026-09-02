"""
schemas.py - Pydantic data schemas for ID Document Extraction Pipeline.
Defines data structures for OCR bounding boxes, document types (Front & Back), and extracted fields.
"""

from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates and text metadata extracted from OCR."""
    text: str = Field(..., description="Detected text token")
    confidence: float = Field(..., description="OCR confidence score (0-100)")
    x: int = Field(..., description="X coordinate of top-left corner")
    y: int = Field(..., description="Y coordinate of top-left corner")
    width: int = Field(..., description="Width of bounding box")
    height: int = Field(..., description="Height of bounding box")


class OCRResult(BaseModel):
    """Aggregate result from OCR engine."""
    words: List[BoundingBox] = Field(default_factory=list, description="List of recognized word tokens with bounding boxes")
    raw_text: str = Field("", description="Raw concatenated text from document")
    layout_text: str = Field("", description="Spatial layout preserved text formatted for LLM")
    average_confidence: float = Field(0.0, description="Average confidence score across all tokens")
    word_count: int = Field(0, description="Total number of valid detected words")


class AadhaarData(BaseModel):
    """Extracted fields for Aadhaar Card Front Side."""
    document_type: Literal["aadhaar"] = "aadhaar"
    name: Optional[str] = Field(None, description="Full name of cardholder")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or raw format")
    year_of_birth: Optional[str] = Field(None, description="Year of birth if full DOB is not present")
    gender: Optional[str] = Field(None, description="Gender (Male/Female/Transgender)")
    aadhaar_number: Optional[str] = Field(None, description="12-digit Aadhaar number (masked in final output)")
    address: Optional[str] = Field(None, description="Complete address if present")


class AadhaarBackData(BaseModel):
    """Extracted fields for Aadhaar Card Back Side."""
    document_type: Literal["aadhaar_back"] = "aadhaar_back"
    care_of: Optional[str] = Field(None, description="Father / Mother / Spouse (C/O, S/O, D/O, W/O)")
    address: Optional[str] = Field(None, description="Complete residential address")
    pincode: Optional[str] = Field(None, description="6-digit postal code")
    state: Optional[str] = Field(None, description="State / Union Territory")
    requires_front_side: bool = Field(True, description="True if front side is required for full verification")


class PANData(BaseModel):
    """Extracted fields for PAN Card Front Side."""
    document_type: Literal["pan"] = "pan"
    name: Optional[str] = Field(None, description="Full name of cardholder")
    father_name: Optional[str] = Field(None, description="Father's name of cardholder")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or raw format")
    pan_number: Optional[str] = Field(None, description="10-character PAN number (e.g. ABCDE1234F)")


class PANBackData(BaseModel):
    """Guidance response for PAN Card Back Side."""
    document_type: Literal["pan_back"] = "pan_back"
    message: str = Field(
        default="PAN Card Back Side contains no personal data. Please flip card and upload the FRONT side.",
        description="User guidance message"
    )
    requires_front_side: bool = Field(True, description="Always true for PAN back")


class DrivingLicenceData(BaseModel):
    """Extracted fields for Driving Licence Front Side."""
    document_type: Literal["driving_licence"] = "driving_licence"
    name: Optional[str] = Field(None, description="Full name of licence holder")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or raw format")
    dl_number: Optional[str] = Field(None, description="Driving licence number")
    address: Optional[str] = Field(None, description="Residential address")
    issue_date: Optional[str] = Field(None, description="Date of issue in YYYY-MM-DD format")
    valid_until: Optional[str] = Field(None, description="Licence expiry date in YYYY-MM-DD format")


class DrivingLicenceBackData(BaseModel):
    """Extracted fields for Driving Licence Back Side."""
    document_type: Literal["driving_licence_back"] = "driving_licence_back"
    vehicle_classes: Optional[List[str]] = Field(default_factory=list, description="Authorised vehicle categories (LMV, MCWG, TRANS)")
    address: Optional[str] = Field(None, description="Permanent address if present on back")
    badge_number: Optional[str] = Field(None, description="Commercial driver badge number if present")
    requires_front_side: bool = Field(True, description="True if front side is required for full verification")


class UnsupportedDocumentData(BaseModel):
    """Response when document is unsupported or unclassified."""
    document_type: Literal["unsupported"] = "unsupported"
    error: str = Field(
        default="Only Aadhaar Card, PAN Card and Driving Licence are supported.",
        description="Error message detailing unsupported document"
    )


# Union type for all supported extracted models
ExtractedData = Union[
    AadhaarData, 
    AadhaarBackData, 
    PANData, 
    PANBackData, 
    DrivingLicenceData, 
    DrivingLicenceBackData, 
    UnsupportedDocumentData
]


class FinalExtractionResult(BaseModel):
    """Final unified payload returned to the UI/API."""
    id: Optional[str] = Field(None, description="Unique stored document ID")
    document_type: str
    is_valid: bool = Field(True, description="True if document is supported and validly parsed")
    short_circuited: bool = Field(False, description="True if decision gate rejected before LLM call")
    is_duplicate_or_sample: bool = Field(False, description="True if duplicate, sample, or specimen watermark detected")
    authenticity_status: str = Field("VERIFIED", description="VERIFIED, DUPLICATE_COPY, or SUSPICIOUS")
    data: ExtractedData
    warnings: List[str] = Field(default_factory=list, description="Validation warnings or data quality alerts")
    ocr_confidence: float = Field(0.0, description="Average OCR confidence score")
    raw_ocr_text: Optional[str] = Field(None, description="Raw OCR text extracted from image")
    quality_report: Optional[Dict[str, Any]] = Field(None, description="Image sharpness and resolution metrics")
    images: Optional[Dict[str, str]] = Field(default_factory=dict, description="Base64 encoded visual pipeline images")
