import hashlib
from database import get_db

def generate_hardware_hash(hw_id: str) -> str:
    """Create a secure hash of the hardware ID to avoid storing raw IDs."""
    return hashlib.sha256(hw_id.encode()).hexdigest()

def verify_device(user_id: str, hw_id: str) -> bool:
    """Verify if the request is coming from the bound hardware."""
    # Bypass security for guest and dev users during testing
    if user_id in ["SCL_Guest_User", "ajay"]:
        return True
        
    db = get_db()
    hashed_hw = generate_hardware_hash(hw_id)
    
    response = db.table("profiles").select("hardware_id").eq("user_id", user_id).single().execute()
    
    if response.data and response.data.get("hardware_id") == hashed_hw:
        return True
    return False

def bind_device(username: str, hw_id: str, device_type: str):
    """Bind a new device to a user profile. Uses upsert to avoid duplicate errors."""
    db = get_db()
    hashed_hw = generate_hardware_hash(hw_id)
    
    data = {
        "username": username,
        "hardware_id": hashed_hw,
        "device_type": device_type
    }
    
    # Use upsert and ensure it returns the data
    response = db.table("profiles").upsert(data).execute()
    
    if response.data and len(response.data) > 0:
        user_row = response.data[0]
        # Ensure we return a dictionary with 'user_id' regardless of DB column name (id vs user_id)
        return {
            "user_id": user_row.get("id") or user_row.get("user_id"),
            "username": user_row.get("username"),
            "hardware_id": user_row.get("hardware_id")
        }
    return None
