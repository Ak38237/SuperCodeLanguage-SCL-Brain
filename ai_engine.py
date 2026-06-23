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
        HYBRID MEMORY ENGINE: Combines Permanent Facts + Short-Term Conversation.
        """
        # 1. PERMANENT MEMORY: Fetch core facts about the user
        try:
            memory = self.db.table("brain_memory").select("*").eq("user_id", user_id).execute()
            # Format: "Name: Ajay", "Preference: Python"
            permanent_facts = "\n".join([f"{m['context_key']}: {m['context_value']}" for m in memory.data]) if memory.data else "No permanent facts yet."
        except Exception:
            permanent_facts = "No permanent facts available."
        
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

            # SYSTEM PROMPT: Combining Personality + Permanent Knowledge
            system_prompt = (
                "You are the SCL Unified Brain, a helpful, high-energy, and friendly AI agent. "
                "IMPORTANT: Speak in a natural, brotherly HINGLISH style (mix of Hindi and English). "
                "Don't be too formal. Use words like 'Bhai', 'Yaar', 'Ekdum', 'Mast'. "
                f"USER PERMANENT MEMORY:\n{permanent_facts}\n\n"
                "Use the above facts to personalize your conversation. If the user's name is mentioned, use it!"
            )
            
            if mode == "coding":
                system_prompt += "\nMode: Coding Mentor. Structure: Concept -> Step-by-Step Logic -> Optimized Code -> Pro Tips."
            elif mode == "language":
                system_prompt += "\nMode: Language Coach. Structure: Translation -> Pronunciation -> Grammar Breakdown -> Practice."

            # BUILD THE MESSAGE CHAIN
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add short-term conversational history
            if history:
                for msg in history:
                    messages.append({"role": msg["role"], "content": msg["message"]})
            
            # Current prompt
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
                "temperature": 0.8,
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
