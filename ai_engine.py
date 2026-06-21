import random
from database import get_db

class AIEngine:
    def __init__(self):
        self.db = get_db()

    def get_best_api_key(self, provider: str = "FreeLLM"):
        """
        Rotates through available API keys for a specific provider.
        Fetches a random active key and increments its usage.
        """
        # Fetch active keys for the provider
        response = self.db.table("api_vault").select("*").eq("provider", provider).eq("is_active", True).execute()
        
        if not response.data:
            return None
        
        # Select a random key to distribute load (Rotation)
        selected_key_data = random.choice(response.data)
        key_id = selected_key_data["key_id"]
        api_key = selected_key_data["api_key"]
        
        # Update usage count
        self.db.table("api_vault").update({"usage_count": selected_key_data["usage_count"] + 1}).eq("key_id", key_id).execute()
        
        return api_key

    async def generate_response(self, user_id: str, prompt: str):
        """
        Orchestrates the AI response. 
        1. Fetches context from memory.
        2. Gets a rotated API key.
        3. Calls the LLM (Mocked here, will be integrated with actual APIs).
        """
        # 1. Get context from memory
        memory = self.db.table("brain_memory").select("*").eq("user_id", user_id).execute()
        context = "\n".join([f"{m['context_key']}: {m['context_value']}" for m in memory.data]) if memory.data else ""
        
        # 2. Get Rotated API Key
        api_key = self.get_best_api_key()
        if not api_key:
            return "Error: No active API keys available in the vault."

        # 3. Call LLM (Simulation of the API call)
        full_prompt = f"Context:\n{context}\n\nUser: {prompt}"
        # In real implementation, use requests.post(api_url, json={"prompt": full_prompt, "key": api_key})
        
        response_text = f"[SCL-Unified-Brain]: I processed your request using Key {api_key[:5]}... and context. Your response to '{prompt}' would go here!"
        
        return response_text
