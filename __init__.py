"""
Auto-TDD System - Complete Implementation
==========================================

This is the main entry point for the Auto-TDD system.

SYSTEM COMPONENTS:
├── parser.py             - Natural language prompt parsing
├── test_generator.py     - Comprehensive test suite generation
├── code_generator.py     - AI-powered code generation (CodeLlama)
├── sandbox_runner.py     - Secure Docker-based execution
├── failure_analyzer.py   - Intelligent error analysis
├── refine_loop.py        - RL-based iterative refinement
├── quality_checks.py     - Code quality and security validation
└── cli.py                - Command-line orchestration

QUICK START:
1. Ensure Ollama is running: ollama serve
2. Install dependencies: pip install -r requirements.txt
3. Run: python cli.py --prompt "Your problem description"

EXAMPLES:
python cli.py --prompt "Write a factorial function"
python cli.py --prompt-file examples/fibonacci.txt
python cli.py --prompt "Sort a list" --max-iterations 10 --verbose

DOCUMENTATION:
- README.md         - Complete user guide
- QUICKSTART.md     - 5-minute quick start
- ARCHITECTURE.md   - Technical architecture
- PROJECT_COMPLETE.md - Project summary

For more information, see README.md
"""

__version__ = "1.0.0"
__author__ = "Auto-TDD Project"
__license__ = "MIT"

# Package information
__all__ = [
    'PromptParser',
    'TestGenerator',
    'CodeGenerator',
    'SandboxRunner',
    'FailureAnalyzer',
    'RefinementLoop',
    'QualityChecker',
    'Config',
    'logger',
]

# Import main classes for convenient access
try:
    from parser import PromptParser
    from test_generator import TestGenerator
    from code_generator import CodeGenerator
    from sandbox_runner import SandboxRunner
    from failure_analyzer import FailureAnalyzer
    from refine_loop import RefinementLoop
    from quality_checks import QualityChecker
    from config import Config
    from logger import logger
except ImportError as e:
    print(f"Warning: Could not import all modules: {e}")
    print("Please run: pip install -r requirements.txt")
