"""OpenAI LLM Provider - For test generation with free tier safety."""
import requests
from typing import Optional
from config import Config
from logger import logger

class OpenAIProvider:
    """OpenAI API provider with free tier safety controls."""
    
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.model = Config.OPENAI_MODEL  # gpt-3.5-turbo or gpt-4o-mini
        self.temperature = Config.OPENAI_TEMPERATURE
        self.max_tokens = Config.OPENAI_MAX_TOKENS
        self.timeout = Config.OPENAI_TIMEOUT
        
        # OpenAI API endpoint
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        # Safety limits for free tier
        self.max_tokens_per_request = 1000  # Keep tokens low to avoid charges
        self.request_count = 0
        self.max_requests_per_session = 10  # Safety limit
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set")
    
    def generate(self, prompt: str) -> Optional[str]:
        """Generate tests using OpenAI API with safety checks.
        
        Args:
            prompt: The generation prompt
            
        Returns:
            Generated text or None if failed
        """
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return None
        
        # Safety check: Don't exceed max requests
        if self.request_count >= self.max_requests_per_session:
            logger.error("Max OpenAI requests reached for this session", 
                        count=self.request_count,
                        max=self.max_requests_per_session)
            return None
        
        try:
            # Enforce token limit
            safe_max_tokens = min(self.max_tokens, self.max_tokens_per_request)
            
            logger.info("Calling OpenAI API", 
                       model=self.model,
                       max_tokens=safe_max_tokens,
                       request_num=self.request_count + 1)
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Python test generation expert. Generate comprehensive pytest test cases."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": safe_max_tokens,  # Safety limit
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Increment counter after making request
            self.request_count += 1
            
            if response.status_code == 200:
                result = response.json()
                
                # Log usage for cost tracking
                usage = result.get("usage", {})
                logger.info("OpenAI response received",
                           prompt_tokens=usage.get("prompt_tokens", 0),
                           completion_tokens=usage.get("completion_tokens", 0),
                           total_tokens=usage.get("total_tokens", 0))
                
                # Extract text from response
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        generated_text = choice["message"]["content"]
                        logger.info("OpenAI generation successful", 
                                   length=len(generated_text))
                        return generated_text
                
                logger.error("Unexpected OpenAI response structure", response=result)
                return None
            
            elif response.status_code == 429:
                logger.error("OpenAI rate limit exceeded - wait before retrying")
                return None
            
            elif response.status_code == 401:
                logger.error("OpenAI API key invalid or expired")
                return None
            
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error("OpenAI API error", 
                           status=response.status_code,
                           error=error_data.get("error", {}).get("message", response.text))
                return None
                
        except requests.Timeout:
            logger.error("OpenAI API timeout")
            return None
        except Exception as e:
            logger.error("OpenAI API exception", error=str(e))
            return None
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available and configured."""
        return bool(self.api_key)
    
    def get_request_count(self) -> int:
        """Get number of requests made in this session."""
        return self.request_count
    
    def reset_request_count(self):
        """Reset request counter (use carefully!)."""
        self.request_count = 0
        logger.info("OpenAI request counter reset")
