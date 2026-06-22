import random
import httpx
import asyncio
from database import get_db

class AIEngine:
    def __init__(self):
        self.db = get_db()
        # Mapping providers to their API endpoints
        self.provider_endpoints = {
            "Groq": "https://api.groq.com/openai/v1/chat/completions",
            "OpenAI": "https://api.openai.com/v1/chat/completions",
            "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
            "FreeLLM": "https://api.groq.com/openai/v1/chat/completions"
        }

    def get_best_api_key(self, provider: str = "FreeLLM"):
        """
        Fetches a random active key and its provider.
        """
        try:
            response = self.db.table("api_vault").select("*").eq("is_active", True).execute()
            if not response.data or len(response.data) == 0:
                print("Vault Error: No active keys found in api_vault table.")
                return None
            
            selected_key_data = random.choice(response.data)
            key_id = selected_key_data["key_id"]
            api_key = selected_key_data["api_key"]
            provider = selected_key_data.get("provider", "FreeLLM")
            
            # Update usage count (do this asynchronously if possible, but keeping it simple for now)
            try:
                self.db.table("api_vault").update({"usage_count": selected_key_data.get("usage_count", 0) + 1}).eq("key_id", key_id).execute()
            except Exception as e:
                print(f"Non-critical update error: {e}")
            
            return {"api_key": api_key, "provider": provider}
        except Exception as e:
            print(f"DB Error in get_best_api_key: {e}")
            return None

    async def generate_response(self, user_id: str, prompt: str, mode: str = "general"):
        """
        HIGH-PERFORMANCE ASYNC INTEGRATION: Calls LLM using httpx with specialized modes.
        """
        # 1. Get context from memory
        try:
            memory = self.db.table("brain_memory").select("*").eq("user_id", user_id).execute()
            context = "\n".join([f"{m['context_key']}: {m['context_value']}" for m in memory.data]) if memory.data else ""
        except Exception:
            context = ""
        
        # 2. Get Rotated API Key
        key_info = self.get_best_api_key()
        if not key_info:
            return "Error: No active API keys available in the vault. Please add keys to the database."

        api_key = key_info["api_key"]
        provider = key_info["provider"]
        endpoint = self.provider_endpoints.get(provider, self.provider_endpoints["FreeLLM"])

        # 3. Specialized Prompting Logic
        system_prompt = "You are the SCL Unified Brain, a helpful and high-energy AI agent. Respond concisely and supportively."
        
        if mode == "coding":
            system_prompt = (
                "You are a World-Class Coding Mentor. Your goal is to teach, not just code. "
                "Follow this structure: \n"
                "1. CONCEPT: Explain the logic in simple terms (Basic to Advanced).\n"
                "2. STEP-BY-STEP: Break down the implementation into logical steps.\n"
                "3. OPTIMIZED CODE: Provide clean, commented code.\n"
                "4. PRO-TIPS: Tell the user how to make it faster or more professional.\n"
                "Use a supportive, 'brotherly' tone and keep it high-energy!"
            )
        elif mode == "language":
            system_prompt = (
                "You are an expert Polyglot Language Coach. Do not just translate.\n"
                "Follow this structure:\n"
                "1. TRANSLATION: Accurate translation in the target language.\n"
                "2. PRONUNCIATION: Write it in easy-to-read phonetic English.\n"
                "3. GRAMMAR BREAKDOWN: Explain why specific words/tenses were used.\n"
                "4. PRACTICE: Give the user one similar sentence to try themselves.\n"
                "Be encouraging and friendly!"
            )

        full_prompt = f"System Context:\n{context}\n\nUser: {prompt}"
        
        payload = {
            "model": "llama3-8b-8192" if provider in ["Groq", "FreeLLM"] else "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"API Error ({e.response.status_code}): {e.response.text[:100]}"
        except Exception as e:
            return f"Cloud Brain Connection Error: {str(e)}"
