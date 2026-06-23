import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import security
from ai_engine import AIEngine
from database import get_db

app = FastAPI(title="SCL Unified Brain")
ai = AIEngine()

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

@app.get("/health")
def health_check():
    try:
        db = get_db()
        db.table("profiles").select("count").limit(1).execute()
        return {"status": "Healthy", "database": "Connected", "message": "SCL Brain is fully operational!"}
    except Exception as e:
        return {"status": "Unhealthy", "database": "Disconnected", "error": str(e)}

@app.post("/auth/bind")
async def bind_device(req: BindRequest):
    try:
        user = security.bind_device(req.username, req.hardware_id, req.device_type)
        if not user:
            raise HTTPException(status_code=400, detail="Device binding failed")
        return {"status": "Success", "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Binding Error: {str(e)}")

@app.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint with hardware verification, PERMANENT MEMORY, and AI rotation."""
    try:
        if not security.verify_device(req.user_id, req.hardware_id):
            raise HTTPException(status_code=403, detail="Unauthorized Device Access!")
        
        db = get_db()
        # Fetch last 15 messages for better flow
        try:
            history_res = db.table("chat_history").select("role, message").eq("user_id", req.user_id).order("created_at").execute()
            chat_history = history_res.data[-15:] if history_res.data else []
        except Exception as e:
            print(f"History fetch error: {e}")
            chat_history = []

        response = await ai.generate_response(req.user_id, req.prompt, history=chat_history)
        
        try:
            db.table("chat_history").insert({"user_id": req.user_id, "role": "user", "message": req.prompt}).execute()
            db.table("chat_history").insert({"user_id": req.user_id, "role": "assistant", "message": response}).execute()
        except Exception as db_e:
            print(f"Chat history save error: {db_e}")
        
        return {"response": response}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Global Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/memory/set")
async def set_memory(req: MemoryRequest):
    try:
        if not security.verify_device(req.user_id, req.hardware_id):
            raise HTTPException(status_code=403, detail="Unauthorized Device Access!")
        db = get_db()
        db.table("brain_memory").upsert({"user_id": req.user_id, "context_key": req.key, "context_value": req.value}).execute()
        return {"status": "Memory Updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
