"""Gemini LLM Provider - Google Gemini API integration."""
import requests
from typing import Optional
from config import Config
from logger import logger

class GeminiProvider:
    """Google Gemini API provider for code generation."""
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL
        self.temperature = Config.GEMINI_TEMPERATURE
        self.max_tokens = Config.GEMINI_MAX_TOKENS
        self.timeout = Config.GEMINI_TIMEOUT
        
        # Gemini API endpoint - don't add models/ prefix if already present
        model_path = self.model if self.model.startswith("models/") else f"models/{self.model}"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set, will use fallback")
    
    def generate(self, prompt: str) -> Optional[str]:
        """Generate code using Gemini API.
        
        Args:
            prompt: The generation prompt
            
        Returns:
            Generated text or None if failed
        """
        if not self.api_key:
            logger.error("Gemini API key not configured")
            return None
        
        try:
            logger.info("Calling Gemini API", model=self.model)
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens,
                    "topP": 0.95,
                    "topK": 40,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add API key to URL
            url = f"{self.api_url}?key={self.api_key}"
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from Gemini response
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    
                    # Check for MAX_TOKENS finish reason
                    finish_reason = candidate.get("finishReason", "")
                    if finish_reason == "MAX_TOKENS":
                        logger.warning("Gemini hit MAX_TOKENS limit, response may be incomplete")
                    elif finish_reason:
                        logger.debug("Gemini finish reason", reason=finish_reason)
                    
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            generated_text = parts[0]["text"]
                            logger.info("Gemini response received", 
                                       length=len(generated_text),
                                       finish_reason=finish_reason)
                            
                            # DEBUG: Log last 200 chars to check if code is complete
                            logger.debug("Response end preview", 
                                        end_preview=generated_text[-200:] if len(generated_text) > 200 else generated_text)
                            return generated_text
                
                logger.error("Unexpected Gemini response structure", response=result)
                return None
            else:
                logger.error("Gemini API error", 
                           status=response.status_code,
                           error=response.text)
                return None
                
        except requests.Timeout:
            logger.error("Gemini API timeout")
            return None
        except Exception as e:
            logger.error("Gemini API exception", error=str(e))
            return None
    
    def is_available(self) -> bool:
        """Check if Gemini API is available and configured."""
        return bool(self.api_key)
