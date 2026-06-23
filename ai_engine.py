import random
import httpx
import asyncio
from database import get_db

class AIEngine:
    def __init__(self):
        self.db = get_db()
        self.provider_endpoints = {
            "Groq": "https://api.groq.com/openai/v1/chat/completions",
            "OpenAI": "https://api.openai.com/v1/chat/completions",
            "DeepSeek": "https://api.deepseek.com/v1/chat/completions",
            "Nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
            "FreeLLM": "https://api.groq.com/openai/v1/chat/completions"
        }

    def get_best_api_key(self, provider: str = "FreeLLM"):
        try:
            response = self.db.table("api_vault").select("*").eq("is_active", True).execute()
            if not response.data or len(response.data) == 0:
                return None
            selected_key_data = random.choice(response.data)
            return {"api_key": selected_key_data["api_key"], "provider": selected_key_data.get("provider", "FreeLLM")}
        except Exception:
            return None

    async def generate_response(self, user_id: str, prompt: str, history: list = None, mode: str = "general"):
        """
        ULTRA-RESILIENT ASYNC INTEGRATION: Now with SHORT-TERM CONVERSATIONAL MEMORY.
        """
        try:
            memory = self.db.table("brain_memory").select("*").eq("user_id", user_id).execute()
            context = "\n".join([f"{m['context_key']}: {m['context_value']}" for m in memory.data]) if memory.data else ""
        except Exception:
            context = ""
        
        max_retries = 3
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            key_info = self.get_best_api_key()
            if not key_info: return "Error: No active API keys in vault."

            api_key = key_info["api_key"]
            provider_raw = key_info["provider"]
            
            provider = "FreeLLM"
            provider_lower = provider_raw.lower()
            if "groq" in provider_lower: provider = "Groq"
            elif "openai" in provider_lower: provider = "OpenAI"
            elif "deepseek" in provider_lower: provider = "DeepSeek"
            elif "nvidia" in provider_lower: provider = "Nvidia"
            
            endpoint = self.provider_endpoints.get(provider)
            if not endpoint: continue

            system_prompt = "You are the SCL Unified Brain, a helpful and high-energy AI agent."
            if mode == "coding":
                system_prompt = "You are a World-Class Coding Mentor. Teach concept -> Step-by-Step Logic -> Optimized Code -> Pro Tips."
            elif mode == "language":
                system_prompt = "You are an expert Polyglot Coach. Provide Translation -> Pronunciation -> Grammar Breakdown -> Practice."

            # CONSTRUCTING THE MEMORY-AWARE MESSAGE LIST
            messages = [{"role": "system", "content": f"{system_prompt}\n\nUser Context:\n{context}"}]
            
            # Add previous conversation history
            if history:
                for msg in history:
                    messages.append({"role": msg["role"], "content": msg["message"]})
            
            # Add the current prompt
            messages.append({"role": "user", "content": prompt})
            
            model_map = {
                "Groq": "llama-3.1-8b-instant",
                "OpenAI": "gpt-3.5-turbo",
                "DeepSeek": "deepseek-chat",
                "Nvidia": "meta/llama-3.1-8b-instruct",
                "FreeLLM": "llama-3.1-8b-instant"
            }
            selected_model = model_map.get(provider, "llama-3.1-8b-instant")
            
            payload = {
                "model": selected_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    if response.status_code == 401: continue
                    response.raise_for_status()
                    return response.json()['choices'][0]['message']['content']
            except Exception:
                continue
        
        return "Error: All available API keys are currently failing."
