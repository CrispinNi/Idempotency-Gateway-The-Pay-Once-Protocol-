import hashlib
import json

def hash_payload(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()