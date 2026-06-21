import hashlib
from database import get_db

def generate_hardware_hash(hw_id: str) -> str:
    """Create a secure hash of the hardware ID to avoid storing raw IDs."""
    return hashlib.sha256(hw_id.encode()).hexdigest()

def verify_device(user_id: str, hw_id: str) -> bool:
    """Verify if the request is coming from the bound hardware."""
    db = get_db()
    hashed_hw = generate_hardware_hash(hw_id)
    
    response = db.table("profiles").select("hardware_id").eq("user_id", user_id).single().execute()
    
    if response.data and response.data.get("hardware_id") == hashed_hw:
        return True
    return False

def bind_device(username: str, hw_id: str, device_type: str):
    """Bind a new device to a user profile."""
    db = get_db()
    hashed_hw = generate_hardware_hash(hw_id)
    
    data = {
        "username": username,
        "hardware_id": hashed_hw,
        "device_type": device_type
    }
    
    response = db.table("profiles").insert(data).execute()
    return response.data[0] if response.data else None
