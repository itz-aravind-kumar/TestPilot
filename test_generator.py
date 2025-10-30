"""Test Generator Module - Generates comprehensive test suites using LLM."""
import json
import requests
from typing import List, Dict, Any

from parser import ProblemSpec
from logger import logger
from config import Config
from utils import validate_python_syntax

class TestGenerator:
    """Generates pytest test suites from problem specifications using LLM."""
    
    def __init__(self):
        self.test_count = 0
        self.provider = Config.TEST_LLM_PROVIDER
        
        # Initialize providers based on config
        if self.provider == "openai":
            from openai_provider import OpenAIProvider
            self.openai = OpenAIProvider()
            logger.info("Test generator using OpenAI API")
        elif self.provider == "gemini":
            from gemini_provider import GeminiProvider
            self.gemini = GeminiProvider()
            logger.info("Test generator using Gemini API")
        else:
            # Ollama setup
            self.ollama_url = f"{Config.OLLAMA_HOST}/api/generate"
            self.model = Config.OLLAMA_MODEL
            self.temperature = 0.2
            self.max_tokens = Config.OLLAMA_MAX_TOKENS
    
    def generate(self, spec: ProblemSpec) -> str:
        """Generate complete test suite for given specification using LLM.
        
        Args:
            spec: Problem specification
            
        Returns:
            Complete pytest test code as string
        """
        logger.info("Generating tests", function=spec.function_name)
        
        # Build prompt for LLM
        prompt = self._build_test_generation_prompt(spec)
        
        # Call appropriate LLM provider
        if self.provider == "openai":
            test_code = self._call_openai(prompt)
        elif self.provider == "gemini":
            test_code = self._call_gemini(prompt)
        else:
            test_code = self._call_ollama(prompt)
        
        if not test_code:
            error_msg = f"Failed to generate tests using {self.provider}. LLM did not return any code."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Extract test code from LLM response
        test_code = self._extract_code(test_code)
        
        # Validate syntax
        is_valid, error = validate_python_syntax(test_code)
        if not is_valid:
            # Save problematic test code for debugging
            from pathlib import Path
            debug_file = Path("c:/Auto TTD/logs/last_failed_test_generation.py")
            debug_file.write_text(f"# SYNTAX ERROR: {error}\n\n{test_code}", encoding='utf-8')
            
            error_msg = f"Generated tests have syntax errors: {error}\nSaved to {debug_file}"
            logger.error(error_msg)
            
            # Try to regenerate once more with a clearer prompt
            logger.warning("Attempting to regenerate tests with stricter instructions...")
            retry_prompt = self._build_test_generation_prompt(spec) + "\n\nIMPORTANT: Ensure ALL parentheses, brackets, and quotes are properly closed!"
            
            if self.provider == "openai":
                test_code = self._call_openai(retry_prompt)
            elif self.provider == "gemini":
                test_code = self._call_gemini(retry_prompt)
            else:
                test_code = self._call_ollama(retry_prompt)
            
            if test_code:
                test_code = self._extract_code(test_code)
                is_valid, error = validate_python_syntax(test_code)
                
                if not is_valid:
                    # Second attempt failed too
                    raise RuntimeError(f"Generated tests have syntax errors after retry: {error}")
                else:
                    logger.info("Successfully regenerated tests on second attempt")
            else:
                raise RuntimeError(f"Failed to regenerate tests: {error}")
        
        # Count tests
        self.test_count = test_code.count("def test_")
        
        logger.info("Generated test suite", 
                   test_count=self.test_count,
                   lines=len(test_code.split('\n')))
        
        return test_code
    
    def _build_test_generation_prompt(self, spec: ProblemSpec) -> str:
        """Build comprehensive prompt for test generation."""
        
        prompt_parts = [
            "You are an expert Python test engineer. Generate a comprehensive pytest test suite.",
            "",
            f"CRITICAL: The function name is '{spec.function_name}' - you MUST import and test this exact function name!",
            "",
            "REQUIREMENTS:",
            f"1. Test the function: {spec.function_name}",
            f"2. Function description: {spec.description}",
        ]
        
        # Add parameter information
        if spec.parameters:
            prompt_parts.append("\nPARAMETERS:")
            for param in spec.parameters:
                param_info = f"  - {param.name}: {param.type_hint}"
                if param.description:
                    param_info += f" ({param.description})"
                prompt_parts.append(param_info)
        
        # Add return type
        if spec.return_type:
            prompt_parts.append(f"\nRETURN TYPE: {spec.return_type}")
        
        # Add examples
        if spec.examples:
            prompt_parts.append("\nEXAMPLES:")
            for i, example in enumerate(spec.examples, 1):
                prompt_parts.append(f"  Example {i}: {example}")
        
        # Add constraints
        if spec.constraints:
            prompt_parts.append("\nCONSTRAINTS:")
            for constraint in spec.constraints:
                prompt_parts.append(f"  - {constraint}")
        
        # Add edge cases
        if spec.edge_cases:
            prompt_parts.append("\nEDGE CASES TO TEST:")
            for edge_case in spec.edge_cases:
                prompt_parts.append(f"  - {edge_case}")
        
        # Add test requirements
        prompt_parts.extend([
            "",
            "GENERATE:",
            f"1. Import statement: from impl import {spec.function_name}",
            "2. Happy path tests - test normal valid inputs",
            "3. Edge case tests - test boundary values, empty inputs, etc.",
            "4. Error handling tests - test invalid inputs raise appropriate errors",
            "5. Property-based tests if applicable",
            "",
            "CRITICAL REQUIREMENTS:",
            "- MUST use: from impl import {spec.function_name}",
            f"- MUST test the function named: {spec.function_name}",
            "- Each test must have a clear docstring",
            f"- Use test names like: test_{spec.function_name}_<scenario>",
            "- Include proper assertions with helpful messages",
            "- Write clean, professional test code",
            "",
            f"REMINDER: The function you are testing is called '{spec.function_name}'",
            "",
            "Generate ONLY the test code, no explanations:",
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API to generate test code."""
        try:
            if not hasattr(self, 'openai'):
                logger.error("OpenAI provider not initialized")
                return ""
            
            logger.info("Calling OpenAI for test generation")
            response = self.openai.generate(prompt)
            return response or ""
            
        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            return ""
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API to generate test code."""
        try:
            if not hasattr(self, 'gemini'):
                logger.error("Gemini provider not initialized")
                return ""
            
            logger.info("Calling Gemini for test generation")
            response = self.gemini.generate(prompt)
            return response or ""
            
        except Exception as e:
            logger.error("Gemini API error", error=str(e))
            return ""
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API to generate test code."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            }
            
            logger.info("Calling LLM for test generation", model=self.model)
            
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error("LLM API error", status=response.status_code)
                return ""
                
        except requests.Timeout:
            logger.error("LLM API timeout")
            return ""
        except Exception as e:
            logger.error("LLM API error", error=str(e))
            return ""
    
    def _extract_code(self, llm_response: str) -> str:
        """Extract Python code from LLM response."""
        # Remove markdown code blocks if present
        if "```python" in llm_response:
            code = llm_response.split("```python")[1].split("```")[0]
        elif "```" in llm_response:
            code = llm_response.split("```")[1].split("```")[0]
        else:
            code = llm_response
        
        return code.strip()
