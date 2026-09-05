# New fallback method for ai_engine.py
from typing import Optional, List, Dict
def _openai_fallback(self, system_prompt: str, user_prompt: str, conversation_context: List[Dict] = None, image_path: Optional[str] = None, use_vision: bool = False, groq_error: str = "") -> str:
    """OpenAI + local LLM fallback when Groq fails."""
    try:
        # Try OpenAI
        if Config.OPENAI_KEY:
            return self._query_openai(system_prompt, user_prompt, conversation_context, image_path, use_vision)
        
        # Try local Ollama
        if Config.OLLAMA_URL:
            return self._query_ollama(system_prompt, user_prompt)
        
        return f"{groq_error or '❌'}\\\\n💡 Set OPENAI_API_KEY or install Ollama for fallback."
    except Exception as e:
        return f"❌ Fallback failed: {str(e)}"

def _query_openai(self, system_prompt: str, user_prompt: str, conversation_context: List[Dict] = None, image_path: Optional[str] = None, use_vision: bool = False) -> str:
    """Query OpenAI API."""
    headers = {"Authorization": f"Bearer {Config.OPENAI_KEY}", "Content-Type": "application/json"}
    API_URL = "https://api.openai.com/v1/chat/completions"
    
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_context:
        messages.extend(conversation_context[-10:])
    messages.append({"role": "user", "content": user_prompt})
    
    data = {
        "model": "gpt-4o-mini",  # or gpt-4o
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"OpenAI failed: {e}")
        return "❌ OpenAI unavailable."

def _query_ollama(self, system_prompt: str, user_prompt: str) -> str:
    """Query local Ollama server."""
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    
    data = {
        "model": "llama3.2",  # or local model
        "messages": messages,
        "stream": False
    }
    
    try:
        response = requests.post(f"{Config.OLLAMA_URL}/api/chat", json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result["message"]["content"]
    except Exception as e:
        logger.warning(f"Ollama failed: {e}")
        return "❌ Ollama unavailable. Run 'ollama serve'."
