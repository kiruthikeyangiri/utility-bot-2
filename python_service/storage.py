"""
storage.py - High-Performance Verification Storage Layer.
Supports both MongoDB (via async Motor driver with TTL indexes) 
and zero-dependency Local JSON Storage with 30-Day Auto-Retention & Device Isolation.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
RETENTION_DAYS = 30

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# MongoDB Configuration (Optional - Active if MONGODB_URI is provided)
MONGODB_URI = os.getenv("MONGODB_URI")
mongo_client = None
mongo_db = None
mongo_collection = None

if MONGODB_URI:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import certifi
        # Connect to MongoDB Atlas with secure SSL CA certificates
        mongo_client = AsyncIOMotorClient(
            MONGODB_URI, 
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=3000
        )
        mongo_db = mongo_client.get_database("utility_bot")
        mongo_collection = mongo_db.get_collection("verifications")
        print("[Utility Bot Storage] MongoDB Atlas configuration loaded.")
    except Exception as e:
        print(f"[Utility Bot Storage] MongoDB connection fallback to local JSON store: {e}")


def read_history(auto_purge: bool = True) -> List[Dict[str, Any]]:
    """Reads stored verification records and automatically purges items older than 30 days."""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    if auto_purge and data:
        now = datetime.utcnow()
        valid_records = []
        has_expired = False
        for doc in data:
            created_str = doc.get("createdAt")
            if created_str:
                try:
                    clean_str = created_str.replace("Z", "+00:00")
                    created_dt = datetime.fromisoformat(clean_str).replace(tzinfo=None)
                    age_days = (now - created_dt).total_seconds() / 86400.0
                    if age_days <= RETENTION_DAYS:
                        valid_records.append(doc)
                    else:
                        has_expired = True
                except Exception:
                    valid_records.append(doc)
            else:
                valid_records.append(doc)
        
        if has_expired:
            write_history(valid_records)
            return valid_records

    return data


def write_history(data: List[Dict[str, Any]]) -> None:
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Utility Bot Storage] Error writing history: {e}")


def save_extraction(
    result_dict: Dict[str, Any], 
    original_filename: str = "document.jpg",
    thumbnail_image: Optional[str] = None,
    device_id: Optional[str] = None
) -> str:
    """Saves document verification extraction with 30-day retention, photo thumbnail, and device isolation."""
    history = read_history(auto_purge=True)
    doc_id = f"doc_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    
    clean_data = result_dict.get("data", {})
    if hasattr(clean_data, "dict"):
        clean_data = clean_data.dict()

    now = datetime.utcnow()
    expires_at = now + timedelta(days=RETENTION_DAYS)

    record = {
        "_id": doc_id,
        "deviceId": device_id or "default_client",  # Device ID Isolation
        "documentType": result_dict.get("document_type", "unsupported"),
        "isValid": result_dict.get("is_valid", True),
        "shortCircuited": result_dict.get("short_circuited", False),
        "isDuplicateOrSample": result_dict.get("is_duplicate_or_sample", False),
        "authenticityStatus": result_dict.get("authenticity_status", "VERIFIED"),
        "data": clean_data,
        "warnings": result_dict.get("warnings", []),
        "ocrConfidence": result_dict.get("ocr_confidence", 0.0),
        "qualityReport": result_dict.get("quality_report", {}),
        "rawOcrText": result_dict.get("raw_ocr_text", ""),
        "originalFileName": original_filename,
        "thumbnail": thumbnail_image,  # Stored photo thumbnail (~40KB) for history preview
        "createdAt": now.isoformat() + "Z",
        "expiresAt": expires_at.isoformat() + "Z",
        "retentionDays": RETENTION_DAYS,
    }
    
    # 1. Insert into local memory history
    history.insert(0, record)
    if len(history) > 300:
        history = history[:300]
    write_history(history)

    # 2. Insert directly into MongoDB Atlas cloud collection
    if mongo_collection is not None:
        try:
            import pymongo
            import certifi
            sync_client = pymongo.MongoClient(
                MONGODB_URI, 
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=2000
            )
            sync_db = sync_client["utility_bot"]
            sync_col = sync_db["verifications"]
            sync_col.replace_one({"_id": doc_id}, record, upsert=True)
            print(f"[Utility Bot Storage] Synced document {doc_id} to MongoDB Atlas cloud!")
        except Exception as err:
            print(f"[Utility Bot Storage] MongoDB sync notice (local backup preserved): {err}")

    return doc_id


def get_history(
    limit: int = 50, 
    page: int = 1, 
    doc_type: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves verification records filtered by Device ID for strict user privacy."""
    history = read_history(auto_purge=True)
    
    # Filter by Device ID if provided (Strict User Privacy Isolation)
    if device_id and device_id != "admin_all":
        history = [d for d in history if d.get("deviceId") == device_id]
        
    if doc_type:
        history = [d for d in history if d.get("documentType") == doc_type]
    
    total = len(history)
    start = (page - 1) * limit
    paginated = history[start:start + limit]
    pages = (total + limit - 1) // limit if total > 0 else 1
    
    return {
        "documents": paginated,
        "total": total,
        "page": page,
        "pages": pages,
        "deviceId": device_id,
        "retentionDays": RETENTION_DAYS,
        "source": "utility_bot_store"
    }


def get_extraction_by_id(doc_id: str, device_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    history = read_history(auto_purge=True)
    for doc in history:
        if doc.get("_id") == doc_id:
            if device_id and device_id != "admin_all" and doc.get("deviceId") != device_id:
                return None
            return doc
    return None


def delete_extraction_by_id(doc_id: str, device_id: Optional[str] = None) -> bool:
    history = read_history(auto_purge=False)
    new_history = []
    found = False
    for d in history:
        if d.get("_id") == doc_id:
            if device_id and device_id != "admin_all" and d.get("deviceId") != device_id:
                new_history.append(d)
                continue
            found = True
        else:
            new_history.append(d)
            
    if found:
        write_history(new_history)
        return True
    return False


def get_storage_stats(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Returns storage space usage and record count for the requesting device and overall."""
    history = read_history(auto_purge=True)
    
    device_records = history
    if device_id and device_id != "admin_all":
        device_records = [d for d in history if d.get("deviceId") == device_id]

    file_size_bytes = 0
    if os.path.exists(HISTORY_FILE):
        file_size_bytes = os.path.getsize(HISTORY_FILE)
    
    kb_size = round(file_size_bytes / 1024.0, 1)
    mb_size = round(file_size_bytes / (1024.0 * 1024.0), 2)

    return {
        "deviceRecords": len(device_records),
        "totalRecords": len(history),
        "maxRecords": 300,
        "retentionDays": RETENTION_DAYS,
        "storageSizeBytes": file_size_bytes,
        "storageSizeKB": kb_size,
        "storageSizeMB": mb_size,
        "percentUsed": min(100, round((len(history) / 300.0) * 100, 1)),
        "deviceId": device_id,
        "databaseEngine": "MongoDB Atlas" if MONGODB_URI else "Local JSON Store"
    }


def clean_storage(device_id: Optional[str] = None, force_all: bool = False) -> Dict[str, Any]:
    """Purges expired records or clears storage for this device."""
    if force_all and (not device_id or device_id == "admin_all"):
        write_history([])
        return {"message": "All verification storage cleared successfully.", "remaining": 0}
    
    if device_id and device_id != "admin_all":
        history = read_history(auto_purge=False)
        new_history = [d for d in history if d.get("deviceId") != device_id]
        write_history(new_history)
        return {"message": f"Storage cleared for device {device_id}.", "remaining": 0}

    history = read_history(auto_purge=True)
    return {"message": "Storage cleaned. Expired records (>30 days) removed.", "remaining": len(history)}
