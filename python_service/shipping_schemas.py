"""
shipping_schemas.py - Pydantic Data Models for Shipping Label Extraction.
Strictly adheres to standard enterprise shipping specifications.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ShipToContact(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class ShipFromContact(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class OrderInformation(BaseModel):
    order_id: Optional[str] = None
    tracking_number: Optional[str] = None
    awb_number: Optional[str] = None
    shipping_date: Optional[str] = None
    payment_type: Optional[str] = None
    remarks: Optional[str] = None


class PackageInformation(BaseModel):
    weight: Optional[str] = None
    dimensions: Optional[str] = None


class ShippingItem(BaseModel):
    product: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    currency: Optional[str] = "INR"
    total: Optional[float] = None


class CodeItem(BaseModel):
    format: str
    value: str


class ShippingLabelResult(BaseModel):
    document_type: str = "shipping_label"
    courier: Optional[str] = None
    ship_to: ShipToContact = Field(default_factory=ShipToContact)
    ship_from: ShipFromContact = Field(default_factory=ShipFromContact)
    order: OrderInformation = Field(default_factory=OrderInformation)
    package: PackageInformation = Field(default_factory=PackageInformation)
    items: List[ShippingItem] = Field(default_factory=list)
    barcodes: List[CodeItem] = Field(default_factory=list)
    qr_codes: List[CodeItem] = Field(default_factory=list)
    ocr_confidence: float = 0.0
    raw_ocr_text: Optional[str] = ""
    warnings: List[str] = Field(default_factory=list)
    image_name: Optional[str] = None
    image_index: int = 1
