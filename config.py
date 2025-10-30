"""Configuration management for Auto-TDD system."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class."""
    
    # LLM Provider Settings
    # TEST_GENERATOR: Use CodeLlama (specialized for test generation)
    # CODE_GENERATOR: Use Gemini (faster, more powerful for implementation)
    
    # Test Generation (CodeLlama via Ollama OR OpenAI)
    TEST_LLM_PROVIDER = os.getenv("TEST_LLM_PROVIDER", "ollama")  # ollama, openai, or gemini
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b")
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # OpenAI (for test generation - free tier safe)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Cheapest: gpt-4o-mini or gpt-3.5-turbo
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))  # Keep low for free tier
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
    
    # Code Generation (Gemini)
    CODE_LLM_PROVIDER = os.getenv("CODE_LLM_PROVIDER", "gemini")  # ollama or gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # gemini-2.5-flash uses internal thoughts
    GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.0"))
    GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "16384"))  # High limit for thoughts + output (2.5 uses ~8K for thoughts)
    GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "60"))
    
    # Sandbox Settings
    DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "auto-tdd-pytest:latest")
    MAX_MEMORY = os.getenv("MAX_MEMORY", "50m")
    CPU_QUOTA = int(os.getenv("CPU_QUOTA", "50000"))
    NETWORK_DISABLED = os.getenv("NETWORK_DISABLED", "true").lower() == "true"
    EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", "30"))
    
    # Refinement Loop Settings
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "5"))
    MIN_IMPROVEMENT_THRESHOLD = float(os.getenv("MIN_IMPROVEMENT_THRESHOLD", "0.1"))
    CONVERGENCE_PATIENCE = int(os.getenv("CONVERGENCE_PATIENCE", "2"))
    
    # RL Reward Settings
    REWARD_TEST_PASS = float(os.getenv("REWARD_TEST_PASS", "10.0"))
    REWARD_QUALITY_BONUS = float(os.getenv("REWARD_QUALITY_BONUS", "5.0"))
    REWARD_EFFICIENCY_BONUS = float(os.getenv("REWARD_EFFICIENCY_BONUS", "3.0"))
    PENALTY_SYNTAX_ERROR = float(os.getenv("PENALTY_SYNTAX_ERROR", "-5.0"))
    PENALTY_RUNTIME_ERROR = float(os.getenv("PENALTY_RUNTIME_ERROR", "-3.0"))
    PENALTY_TIMEOUT = float(os.getenv("PENALTY_TIMEOUT", "-8.0"))
    
    # Paths
    BASE_DIR = Path(__file__).parent
    ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "./artifacts"))
    LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))
    CACHE_DIR = Path(os.getenv("CACHE_DIR", "./.cache"))
    
    # Security Settings
    BLOCKED_IMPORTS = [
        "os", "subprocess", "eval", "exec", "compile",
        "importlib", "sys", "__import__", "open",
        "file", "input", "raw_input"
    ]
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
