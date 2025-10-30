"""Utility functions for Auto-TDD system."""
import ast
import hashlib
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

def validate_python_syntax(code: str) -> tuple[bool, Optional[str]]:
    """Validate Python code syntax using AST parsing.
    
    Args:
        code: Python code string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse error: {str(e)}"

def extract_function_signature(code: str) -> Optional[str]:
    """Extract the main function signature from code.
    
    Args:
        code: Python code string
        
    Returns:
        Function signature or None if not found
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                return f"def {node.name}(...)"
        return None
    except:
        return None

def contains_dangerous_patterns(code: str) -> tuple[bool, List[str]]:
    """Check code for dangerous patterns and imports.
    
    Args:
        code: Python code string
        
    Returns:
        Tuple of (has_dangerous, list_of_violations)
    """
    from config import Config
    
    violations = []
    
    # Check for blocked imports
    for blocked in Config.BLOCKED_IMPORTS:
        patterns = [
            f"import {re.escape(blocked)}",
            f"from {re.escape(blocked)}",
            f"__import__\\(['\"]{ re.escape(blocked)}",
        ]
        for pattern in patterns:
            try:
                if re.search(pattern, code):
                    violations.append(f"Blocked import: {blocked}")
            except re.error:
                # Skip invalid regex patterns
                continue
    
    # Check for eval/exec
    dangerous_funcs = ["eval(", "exec(", "compile(", "__import__("]
    for func in dangerous_funcs:
        if func in code:
            violations.append(f"Dangerous function: {func}")
    
    # Check for file operations
    file_ops = ["open(", "file(", "FileIO("]
    for op in file_ops:
        if op in code:
            violations.append(f"File operation: {op}")
    
    return len(violations) > 0, violations

def calculate_code_hash(code: str) -> str:
    """Calculate SHA-256 hash of code for caching.
    
    Args:
        code: Python code string
        
    Returns:
        Hex digest of code hash
    """
    return hashlib.sha256(code.encode()).hexdigest()

def generate_run_id() -> str:
    """Generate unique run ID with timestamp.
    
    Returns:
        Run ID string like 'run_20250128_143022_abc123'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(
        datetime.now().isoformat().encode()
    ).hexdigest()[:6]
    return f"run_{timestamp}_{random_suffix}"

def sanitize_function_name(name: str) -> str:
    """Sanitize function name to be valid Python identifier.
    
    Args:
        name: Raw function name
        
    Returns:
        Valid Python identifier
    """
    # Remove invalid characters
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure doesn't start with digit
    if name[0].isdigit():
        name = f"func_{name}"
    return name.lower()

def extract_imports(code: str) -> List[str]:
    """Extract all import statements from code.
    
    Args:
        code: Python code string
        
    Returns:
        List of import statements
    """
    imports = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except:
        pass
    return imports

def calculate_complexity(code: str) -> int:
    """Calculate McCabe cyclomatic complexity.
    
    Args:
        code: Python code string
        
    Returns:
        Complexity score
    """
    try:
        tree = ast.parse(code)
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    except:
        return 0

def format_code_with_black(code: str) -> str:
    """Format code using Black formatter.
    
    Args:
        code: Python code string
        
    Returns:
        Formatted code
    """
    try:
        import black
        return black.format_str(code, mode=black.Mode())
    except:
        return code

def truncate_output(output: str, max_length: int = 1000) -> str:
    """Truncate long output for logging.
    
    Args:
        output: Output string
        max_length: Maximum length
        
    Returns:
        Truncated output
    """
    if len(output) <= max_length:
        return output
    return output[:max_length] + f"\n... (truncated {len(output) - max_length} chars)"
