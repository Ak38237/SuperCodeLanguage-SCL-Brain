from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import security
from ai_engine import AIEngine
from database import get_db

app = FastAPI(title="SCL Unified Brain")
ai = AIEngine()

# Models for Request/Response
class BindRequest(BaseModel):
    username: str
    hardware_id: str
    device_type: str

class ChatRequest(BaseModel):
    user_id: str
    hardware_id: str
    prompt: str

class MemoryRequest(BaseModel):
    user_id: str
    hardware_id: str
    key: str
    value: str

@app.get("/")
def read_root():
    return {"status": "SCL Brain is Online", "version": "1.0.0-Alpha"}

@app.post("/auth/bind")
async def bind_device(req: BindRequest):
    """Binds a device to a user profile for secure access."""
    user = security.bind_device(req.username, req.hardware_id, req.device_type)
    if not user:
        raise HTTPException(status_code=400, detail="Device binding failed")
    return {"status": "Success", "user": user}

@app.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint with hardware verification and AI rotation."""
    try:
        # 1. Secure Device Verification
        if not security.verify_device(req.user_id, req.hardware_id):
            raise HTTPException(status_code=403, detail="Unauthorized Device Access! Hacker detected or Hardware mismatch.")
        
        # 2. Generate AI Response
        response = await ai.generate_response(req.user_id, req.prompt)
        
        # 3. Save to Chat History
        try:
            db = get_db()
            db.table("chat_history").insert({
                "user_id": req.user_id,
                "role": "user",
                "message": req.prompt
            }).execute()
            
            db.table("chat_history").insert({
                "user_id": req.user_id,
                "role": "assistant",
                "message": response
            }).execute()
        except Exception as db_e:
            print(f"Chat history save error: {db_e}")
            # We don't raise an error here because the AI response is more important than history
        
        return {"response": response}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Global Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/memory/set")
async def set_memory(req: MemoryRequest):
    """Saves information to the AI's long-term memory."""
    if not security.verify_device(req.user_id, req.hardware_id):
        raise HTTPException(status_code=403, detail="Unauthorized Device Access!")
    
    db = get_db()
    db.table("brain_memory").upsert({
        "user_id": req.user_id,
        "context_key": req.key,
        "context_value": req.value
    }).execute()
    
    return {"status": "Memory Updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
