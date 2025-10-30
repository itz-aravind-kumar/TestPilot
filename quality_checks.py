"""Quality and Safety Checks Module."""
import subprocess
import ast
from typing import Dict, Any, List, Tuple
from pathlib import Path
import tempfile

from logger import logger
from utils import (
    validate_python_syntax, 
    contains_dangerous_patterns,
    calculate_complexity,
    extract_imports
)

class QualityResult:
    """Container for quality check results."""
    
    def __init__(self):
        self.passed = True
        self.errors = []
        self.warnings = []
        self.lint_errors = 0
        self.type_errors = 0
        self.security_issues = 0
        self.complexity = 0
        self.lines = 0
        self.syntax_error = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'passed': self.passed,
            'errors': self.errors,
            'warnings': self.warnings,
            'lint_errors': self.lint_errors,
            'type_errors': self.type_errors,
            'security_issues': self.security_issues,
            'complexity': self.complexity,
            'lines': self.lines,
            'syntax_error': self.syntax_error
        }

class QualityChecker:
    """Performs quality and security checks on generated code."""
    
    def __init__(self):
        self.strict_mode = False
    
    def check(self, code: str) -> Dict[str, Any]:
        """Run all quality checks on code.
        
        Args:
            code: Python code to check
            
        Returns:
            Dictionary with quality metrics
        """
        logger.debug("Running quality checks")
        
        result = QualityResult()
        
        # 1. Syntax check
        is_valid, syntax_error = validate_python_syntax(code)
        if not is_valid:
            result.syntax_error = True
            result.passed = False
            result.errors.append(f"Syntax error: {syntax_error}")
            logger.warning("Syntax check failed", error=syntax_error)
        
        # 2. Security check
        has_danger, violations = contains_dangerous_patterns(code)
        if has_danger:
            result.security_issues = len(violations)
            result.passed = False
            result.errors.extend(violations)
            logger.warning("Security issues found", count=len(violations))
        
        # 3. Complexity analysis
        complexity = calculate_complexity(code)
        result.complexity = complexity
        if complexity > 15:
            result.warnings.append(f"High complexity: {complexity}")
            logger.info("High complexity detected", complexity=complexity)
        
        # 4. Line count
        result.lines = len([l for l in code.split('\n') if l.strip()])
        
        # 5. Lint check (flake8)
        lint_result = self._run_flake8(code)
        result.lint_errors = lint_result['error_count']
        if lint_result['errors']:
            result.warnings.extend(lint_result['errors'][:5])  # Limit warnings
        
        # 6. Type check (mypy) - optional, may be slow
        if self.strict_mode:
            type_result = self._run_mypy(code)
            result.type_errors = type_result['error_count']
            if type_result['errors']:
                result.warnings.extend(type_result['errors'][:3])
        
        logger.debug("Quality checks completed",
                    passed=result.passed,
                    errors=len(result.errors),
                    warnings=len(result.warnings))
        
        return result.to_dict()
    
    def _run_flake8(self, code: str) -> Dict[str, Any]:
        """Run flake8 linter on code.
        
        Args:
            code: Python code
            
        Returns:
            Dictionary with lint results
        """
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # Run flake8
            result = subprocess.run(
                ['flake8', temp_file, '--max-line-length=100', 
                 '--ignore=E501,W503,E203'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse output
            errors = []
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Extract error message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            errors.append(parts[3].strip())
            
            # Clean up
            Path(temp_file).unlink(missing_ok=True)
            
            return {
                'error_count': len(errors),
                'errors': errors
            }
            
        except subprocess.TimeoutExpired:
            logger.warning("Flake8 timeout")
            return {'error_count': 0, 'errors': []}
        except FileNotFoundError:
            # flake8 not installed
            logger.debug("Flake8 not available")
            return {'error_count': 0, 'errors': []}
        except Exception as e:
            logger.warning("Flake8 check failed", error=str(e))
            return {'error_count': 0, 'errors': []}
    
    def _run_mypy(self, code: str) -> Dict[str, Any]:
        """Run mypy type checker on code.
        
        Args:
            code: Python code
            
        Returns:
            Dictionary with type check results
        """
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # Run mypy
            result = subprocess.run(
                ['mypy', temp_file, '--ignore-missing-imports'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # Parse output
            errors = []
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if 'error:' in line:
                        errors.append(line.strip())
            
            # Clean up
            Path(temp_file).unlink(missing_ok=True)
            
            return {
                'error_count': len(errors),
                'errors': errors
            }
            
        except subprocess.TimeoutExpired:
            logger.warning("Mypy timeout")
            return {'error_count': 0, 'errors': []}
        except FileNotFoundError:
            # mypy not installed
            logger.debug("Mypy not available")
            return {'error_count': 0, 'errors': []}
        except Exception as e:
            logger.warning("Mypy check failed", error=str(e))
            return {'error_count': 0, 'errors': []}
    
    def check_imports(self, code: str) -> Tuple[bool, List[str]]:
        """Check if all imports are safe and available.
        
        Args:
            code: Python code
            
        Returns:
            Tuple of (all_safe, list_of_issues)
        """
        imports = extract_imports(code)
        issues = []
        
        from config import Config
        
        for imp in imports:
            # Check against blocked list
            if imp in Config.BLOCKED_IMPORTS:
                issues.append(f"Blocked import: {imp}")
        
        return len(issues) == 0, issues
    
    def suggest_improvements(self, code: str) -> List[str]:
        """Suggest code improvements.
        
        Args:
            code: Python code
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for docstrings
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        suggestions.append(
                            f"Add docstring to function '{node.name}'"
                        )
        except:
            pass
        
        # Check complexity
        complexity = calculate_complexity(code)
        if complexity > 10:
            suggestions.append(
                f"Consider refactoring to reduce complexity (current: {complexity})"
            )
        
        # Check line length
        long_lines = [
            i+1 for i, line in enumerate(code.split('\n')) 
            if len(line) > 100
        ]
        if long_lines:
            suggestions.append(
                f"Lines {long_lines[:3]} exceed 100 characters"
            )
        
        return suggestions
