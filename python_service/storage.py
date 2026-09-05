"""
storage.py - High-Performance Verification Storage Layer.
Supports Human-in-the-Loop Confirmation Gateway, Dual Collections:
- 'verifications' (Success with sequential ID 'IMG000001', 'IMG000002'...)
- 'failed_verifications' (Audit Failed with sequential ID 'FAIL000001', 'FAIL000002'...)
With 30-Day Auto-Retention, Photo Thumbnails & Device Privacy Isolation.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
FAILED_HISTORY_FILE = os.path.join(DATA_DIR, "failed_history.json")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")
RETENTION_DAYS = 30

os.makedirs(DATA_DIR, exist_ok=True)
for file_path in [HISTORY_FILE, FAILED_HISTORY_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)

if not os.path.exists(COUNTERS_FILE):
    with open(COUNTERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"IMG": 0, "FAIL": 0}, f)

# ---------------------------------------------------------------------------
# MongoDB Atlas Data API (HTTPS REST) — Bypasses Python 3.14 TLS issues
# Requires: MONGODB_DATA_API_KEY and MONGODB_APP_ID in .env
# ---------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI")          # kept for display/compat only
MONGODB_DATA_API_KEY = os.getenv("MONGODB_DATA_API_KEY", "")
MONGODB_APP_ID = os.getenv("MONGODB_APP_ID", "")
MONGODB_DB_NAME = "utility_bot"
MONGODB_CLUSTER = "Cluster0"

# Build the Data API base URL from App ID if available
_ATLAS_DATA_URL = f"https://data.mongodb-api.com/app/{MONGODB_APP_ID}/endpoint/data/v1" if MONGODB_APP_ID else ""

IS_MONGO_ONLINE = False

def _atlas_request(action: str, collection: str, body: dict) -> dict:
    """Send a request to MongoDB Atlas Data API (HTTPS POST). Thread-safe, no TLS issues."""
    if not _ATLAS_DATA_URL or not MONGODB_DATA_API_KEY:
        return {}
    import urllib.request
    url = f"{_ATLAS_DATA_URL}/action/{action}"
    payload = {
        "dataSource": MONGODB_CLUSTER,
        "database": MONGODB_DB_NAME,
        "collection": collection,
        **body
    }
    data = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": MONGODB_DATA_API_KEY,
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        raise RuntimeError(f"Atlas Data API error: {err}") from err

# Check Atlas Data API availability at startup
if MONGODB_APP_ID and MONGODB_DATA_API_KEY:
    try:
        result = _atlas_request("find", "verifications", {"limit": 1, "filter": {}})
        IS_MONGO_ONLINE = True
        print("[Utility Bot Storage] MongoDB Atlas Data API connection verified! Cloud sync active.")
    except Exception as _e:
        IS_MONGO_ONLINE = False
        print(f"[Utility Bot Storage] MongoDB Atlas Data API unavailable: {_e}. Using local JSON storage.")
else:
    IS_MONGO_ONLINE = False
    if MONGODB_URI:
        print("[Utility Bot Storage] MONGODB_DATA_API_KEY / MONGODB_APP_ID not set — using local JSON storage. See .env setup.")


def get_next_sequence_id(prefix: str = "IMG") -> str:
    """
    Generates atomic sequential IDs:
    - 'IMG000001', 'IMG000002'... for verified Success records
    - 'FAIL000001', 'FAIL000002'... for audit Failed records
    """
    counters = {"IMG": 0, "FAIL": 0}
    if os.path.exists(COUNTERS_FILE):
        try:
            with open(COUNTERS_FILE, "r", encoding="utf-8") as f:
                counters.update(json.load(f))
        except Exception:
            pass

    counters[prefix] = counters.get(prefix, 0) + 1

    # Sync counter with MongoDB Atlas Data API if live
    if IS_MONGO_ONLINE:
        try:
            # Upsert counter document via Atlas Data API
            _atlas_request("updateOne", "counters", {
                "filter": {"_id": prefix},
                "update": {"$inc": {"seq": 1}, "$setOnInsert": {"_id": prefix}},
                "upsert": True
            })
            # Read back updated counter
            res = _atlas_request("findOne", "counters", {"filter": {"_id": prefix}})
            if res and res.get("document") and "seq" in res["document"]:
                counters[prefix] = max(counters[prefix], int(res["document"]["seq"]))
        except Exception:
            pass

    try:
        with open(COUNTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(counters, f, indent=2)
    except Exception:
        pass

    return f"{prefix}{counters[prefix]:06d}"


def read_file_records(file_path: str, auto_purge: bool = True) -> List[Dict[str, Any]]:
    """Reads stored records and automatically purges items older than 30 days."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
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
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(valid_records, f, indent=2)
            except Exception:
                pass
            return valid_records

    return data


def read_history(auto_purge: bool = True) -> List[Dict[str, Any]]:
    """Reads confirmed success verification records ('IMG...')."""
    return read_file_records(HISTORY_FILE, auto_purge=auto_purge)


def read_failed_history(auto_purge: bool = True) -> List[Dict[str, Any]]:
    """Reads failed verification records ('FAIL...')."""
    return read_file_records(FAILED_HISTORY_FILE, auto_purge=auto_purge)


def write_file_records(file_path: str, data: List[Dict[str, Any]]) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Utility Bot Storage] Error writing {file_path}: {e}")


def save_confirmed_verification(
    result_dict: Dict[str, Any],
    action: str = "correct",
    edited_data: Optional[Dict[str, Any]] = None,
    original_filename: str = "document.jpg",
    thumbnail_image: Optional[str] = None,
    portrait_photo: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Saves confirmed human verification:
    - 'correct': Assigns 'IMG000001', sets status='Success', saves to 'verifications' (Visible in History)
    - 'wrong': Assigns 'FAIL000001', sets status='Failed', saves to 'failed_verifications' (Hidden from History)
    """
    prefix = "IMG" if action == "correct" else "FAIL"
    seq_id = get_next_sequence_id(prefix)
    status = "Success" if action == "correct" else "Failed"
    audit_action = "CORRECT" if action == "correct" else "WRONG"
    target_file = HISTORY_FILE if action == "correct" else FAILED_HISTORY_FILE
    target_collection_name = "verifications" if action == "correct" else "failed_verifications"

    clean_data = edited_data or result_dict.get("data", {})
    if hasattr(clean_data, "dict"):
        clean_data = clean_data.dict()
    elif hasattr(clean_data, "model_dump"):
        clean_data = clean_data.model_dump()

    now = datetime.utcnow()
    expires_at = now + timedelta(days=RETENTION_DAYS)

    record = {
        "_id": seq_id,
        "sequentialId": seq_id,
        "status": status,
        "auditAction": audit_action,
        "deviceId": device_id or "default_client",
        "documentType": result_dict.get("document_type", "unsupported"),
        "isValid": True if action == "correct" else False,
        "shortCircuited": result_dict.get("short_circuited", False),
        "isDuplicateOrSample": result_dict.get("is_duplicate_or_sample", False),
        "authenticityStatus": result_dict.get("authenticity_status", "VERIFIED"),
        "data": clean_data,
        "warnings": result_dict.get("warnings", []),
        "ocrConfidence": result_dict.get("ocr_confidence", 0.0),
        "rawOcrText": result_dict.get("raw_ocr_text", ""),
        "qualityReport": result_dict.get("quality_report", {}),
        "originalFileName": original_filename,
        "thumbnail": thumbnail_image,
        "portraitPhoto": portrait_photo or result_dict.get("portrait_photo"),
        "createdAt": now.isoformat() + "Z",
        "expiresAt": expires_at.isoformat() + "Z",
        "retentionDays": RETENTION_DAYS,
    }

    # 1. Insert into local storage
    records = read_file_records(target_file, auto_purge=True)
    records.insert(0, record)
    if len(records) > 500:
        records = records[:500]
    write_file_records(target_file, records)

    # 2. Sync to MongoDB Atlas via Data API (HTTPS) if live
    if IS_MONGO_ONLINE:
        try:
            _atlas_request("replaceOne", target_collection_name, {
                "filter": {"_id": seq_id},
                "replacement": record,
                "upsert": True
            })
            print(f"[Utility Bot Storage] Synced {seq_id} ({status}) to MongoDB Atlas '{target_collection_name}' via Data API!")
        except Exception as err:
            print(f"[Utility Bot Storage] MongoDB sync notice (local backup preserved): {err}")

    return {
        "id": seq_id,
        "sequential_id": seq_id,
        "status": status,
        "audit_action": audit_action,
        "collection": target_collection_name,
        "record": record
    }


def save_extraction(
    result_dict: Dict[str, Any], 
    original_filename: str = "document.jpg",
    thumbnail_image: Optional[str] = None,
    device_id: Optional[str] = None
) -> str:
    """Legacy helper for initial extraction before human confirmation."""
    doc_id = f"temp_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    return doc_id


def get_history(
    limit: int = 50, 
    page: int = 1, 
    doc_type: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves verified SUCCESS records strictly with 'IMG...' series for the public History drawer."""
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


def get_failed_history(
    limit: int = 50, 
    page: int = 1, 
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves FAILED audit records strictly with 'FAIL...' series for internal audit."""
    failed = read_failed_history(auto_purge=True)
    if device_id and device_id != "admin_all":
        failed = [d for d in failed if d.get("deviceId") == device_id]
        
    total = len(failed)
    start = (page - 1) * limit
    paginated = failed[start:start + limit]
    pages = (total + limit - 1) // limit if total > 0 else 1
    
    return {
        "documents": paginated,
        "total": total,
        "page": page,
        "pages": pages,
        "deviceId": device_id,
        "source": "failed_verifications"
    }


def get_extraction_by_id(doc_id: str, device_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    history = read_history(auto_purge=True)
    for doc in history:
        if doc.get("_id") == doc_id or doc.get("sequentialId") == doc_id:
            if device_id and device_id != "admin_all" and doc.get("deviceId") != device_id:
                return None
            return doc
    return None


def delete_extraction_by_id(doc_id: str, device_id: Optional[str] = None) -> bool:
    history = read_history(auto_purge=False)
    new_history = []
    found = False
    for d in history:
        if d.get("_id") == doc_id or d.get("sequentialId") == doc_id:
            if device_id and device_id != "admin_all" and d.get("deviceId") != device_id:
                new_history.append(d)
                continue
            found = True
        else:
            new_history.append(d)
            
    if found:
        write_file_records(HISTORY_FILE, new_history)
        if IS_MONGO_ONLINE:
            try:
                _atlas_request("deleteOne", "verifications", {"filter": {"_id": doc_id}})
            except Exception:
                pass
        return True
    return False


def get_storage_stats(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Returns storage space usage and record count for the requesting device and overall."""
    history = read_history(auto_purge=True)
    failed = read_failed_history(auto_purge=True)
    
    device_records = history
    if device_id and device_id != "admin_all":
        device_records = [d for d in history if d.get("deviceId") == device_id]

    file_size_bytes = 0
    for fp in [HISTORY_FILE, FAILED_HISTORY_FILE]:
        if os.path.exists(fp):
            file_size_bytes += os.path.getsize(fp)
    
    kb_size = round(file_size_bytes / 1024.0, 1)
    mb_size = round(file_size_bytes / (1024.0 * 1024.0), 2)

    return {
        "deviceRecords": len(device_records),
        "totalSuccessRecords": len(history),
        "totalFailedRecords": len(failed),
        "totalRecords": len(history) + len(failed),
        "maxRecords": 500,
        "retentionDays": RETENTION_DAYS,
        "storageSizeBytes": file_size_bytes,
        "storageSizeKB": kb_size,
        "storageSizeMB": mb_size,
        "percentUsed": min(100, round(((len(history) + len(failed)) / 500.0) * 100, 1)),
        "deviceId": device_id,
        "databaseEngine": "MongoDB Atlas" if MONGODB_URI else "Local JSON Store"
    }


def clean_storage(device_id: Optional[str] = None, force_all: bool = False) -> Dict[str, Any]:
    """Purges expired records or clears storage for this device."""
    if force_all and (not device_id or device_id == "admin_all"):
        write_file_records(HISTORY_FILE, [])
        write_file_records(FAILED_HISTORY_FILE, [])
        return {"message": "All verification storage cleared successfully.", "remaining": 0}
    
    if device_id and device_id != "admin_all":
        history = read_history(auto_purge=False)
        new_history = [d for d in history if d.get("deviceId") != device_id]
        write_file_records(HISTORY_FILE, new_history)

        failed = read_failed_history(auto_purge=False)
        new_failed = [d for d in failed if d.get("deviceId") != device_id]
        write_file_records(FAILED_HISTORY_FILE, new_failed)

        return {"message": f"Storage cleared for device {device_id}.", "remaining": 0}

    history = read_history(auto_purge=True)
    return {"message": "Storage cleaned. Expired records (>30 days) removed.", "remaining": len(history)}
