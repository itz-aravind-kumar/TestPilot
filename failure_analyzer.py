"""Failure Analyzer Module - Analyzes test failures and generates feedback."""
import re
from typing import List, Dict, Any
from sandbox_runner import TestResult

from logger import logger

class FailureAnalysis:
    """Container for failure analysis results."""
    
    def __init__(self):
        self.error_type = "unknown"
        self.failing_tests = []
        self.error_messages = []
        self.stack_traces = []
        self.suggested_fixes = []
        self.root_cause = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "failing_tests": self.failing_tests,
            "error_messages": self.error_messages,
            "root_cause": self.root_cause,
            "suggested_fixes": self.suggested_fixes
        }
    
    def to_feedback(self) -> str:
        """Generate feedback text for code refinement."""
        feedback_parts = []
        
        feedback_parts.append(f"Error Type: {self.error_type}")
        feedback_parts.append(f"\nRoot Cause: {self.root_cause}")
        
        if self.failing_tests:
            feedback_parts.append(f"\nFailing Tests ({len(self.failing_tests)}):")
            for test in self.failing_tests[:10]:  # Increased from 5 to 10
                feedback_parts.append(f"  - {test}")
        
        if self.error_messages:
            feedback_parts.append("\nError Messages:")
            for msg in self.error_messages[:10]:  # Increased from 5 to 10
                feedback_parts.append(f"  {msg}")
        
        if self.suggested_fixes:
            feedback_parts.append("\nSuggested Fixes:")
            for fix in self.suggested_fixes:
                feedback_parts.append(f"  - {fix}")
        
        return "\n".join(feedback_parts)

class FailureAnalyzer:
    """Analyzes test failures and generates actionable feedback."""
    
    def __init__(self):
        self.error_patterns = {
            "assertion": r"AssertionError",
            "type": r"TypeError",
            "value": r"ValueError",
            "attribute": r"AttributeError",
            "index": r"IndexError",
            "key": r"KeyError",
            "zero_division": r"ZeroDivisionError",
            "name": r"NameError",
            "syntax": r"SyntaxError",
            "import": r"ImportError|ModuleNotFoundError",
            "timeout": r"timeout|TIMEOUT",
        }
    
    def analyze(self, test_result: TestResult, code: str = None) -> FailureAnalysis:
        """Analyze test results and generate feedback.
        
        Args:
            test_result: Test execution results
            code: Source code (optional, for better analysis)
            
        Returns:
            FailureAnalysis object
        """
        logger.info("Analyzing test failures",
                   failed=test_result.failed,
                   errors=test_result.errors)
        
        # Log stderr for debugging syntax/import errors
        if test_result.stderr and (test_result.failed == 0 and test_result.passed == 0):
            logger.warning("Test collection error detected",
                          stderr_preview=test_result.stderr[:500])
        
        analysis = FailureAnalysis()
        
        # Classify error type
        analysis.error_type = self._classify_error(test_result)
        
        # Extract failing tests
        analysis.failing_tests = [
            f.get("test", "unknown") 
            for f in test_result.failures
        ]
        
        # Extract error messages
        analysis.error_messages = self._extract_error_messages(test_result)
        
        # DEBUG: Log extracted information
        logger.debug("Failure details extracted",
                    failing_tests=len(analysis.failing_tests),
                    test_names=analysis.failing_tests[:5],
                    error_messages=len(analysis.error_messages),
                    error_preview=analysis.error_messages[:3] if analysis.error_messages else [])
        
        # Determine root cause
        analysis.root_cause = self._determine_root_cause(
            test_result, 
            analysis.error_type
        )
        
        # Generate suggested fixes
        analysis.suggested_fixes = self._generate_suggestions(
            analysis.error_type,
            test_result,
            code
        )
        
        logger.info("Analysis completed",
                   error_type=analysis.error_type,
                   failing_count=len(analysis.failing_tests))
        
        return analysis
    
    def _classify_error(self, test_result: TestResult) -> str:
        """Classify the primary error type.
        
        Args:
            test_result: Test results
            
        Returns:
            Error classification string
        """
        output = test_result.stdout + test_result.stderr
        
        # Check for timeout FIRST
        if test_result.timed_out:
            return "timeout"
        
        # Check for "DID NOT RAISE" BEFORE checking AssertionError
        # This indicates missing validation/error handling
        if "DID NOT RAISE" in output:
            return "partial_failure"  # Will trigger specific error handling suggestions
        
        # Now check each error pattern
        for error_name, pattern in self.error_patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                return error_name
        
        # Check if all tests failed
        if test_result.failed > 0 and test_result.passed == 0:
            return "logic_error"
        
        # Partial failure
        if test_result.failed > 0:
            return "partial_failure"
        
        return "unknown"
    
    def _extract_error_messages(self, test_result: TestResult) -> List[str]:
        """Extract error messages from test output.
        
        Args:
            test_result: Test results
            
        Returns:
            List of error messages
        """
        messages = []
        
        # From structured failures
        for failure in test_result.failures:
            msg = failure.get("message", "")
            if msg:
                # Clean up message
                msg = msg.split('\n')[0][:200]  # First line, limited length
                messages.append(msg)
        
        # From stderr - for syntax/import errors, include more context
        if test_result.stderr:
            stderr_lines = test_result.stderr.split('\n')
            
            # For syntax errors, include the actual error line
            if "SyntaxError" in test_result.stderr:
                for i, line in enumerate(stderr_lines):
                    if "SyntaxError" in line or "^" in line or "File" in line:
                        messages.append(line.strip()[:300])
            
            # For import errors, include the import statement
            elif "ImportError" in test_result.stderr or "ModuleNotFoundError" in test_result.stderr:
                for i, line in enumerate(stderr_lines):
                    if "ImportError" in line or "cannot import" in line or "from impl import" in line:
                        messages.append(line.strip()[:300])
            
            # For other errors, collect error lines
            else:
                for line in stderr_lines:
                    if any(err in line for err in ["Error", "ERROR", "Exception"]):
                        messages.append(line.strip()[:200])
        
        # Check stdout for "DID NOT RAISE" errors - these indicate missing exception handling
        if test_result.stdout and "DID NOT RAISE" in test_result.stdout:
            stdout_lines = test_result.stdout.split('\n')
            for line in stdout_lines:
                if "DID NOT RAISE" in line or "Failed: DID NOT RAISE" in line:
                    # Extract which exception was expected
                    messages.append(f"MISSING VALIDATION: {line.strip()[:300]}")
        
        return messages[:10]  # Increased from 5 to 10 for better context
    
    def _determine_root_cause(self, test_result: TestResult, 
                             error_type: str) -> str:
        """Determine root cause of failures.
        
        Args:
            test_result: Test results
            error_type: Classified error type
            
        Returns:
            Root cause description
        """
        causes = {
            "timeout": "Function runs too long or contains infinite loop",
            "assertion": "Function returns incorrect values",
            "type": "Function called with wrong type or returns wrong type",
            "value": "Function receives or produces invalid values",
            "attribute": "Accessing non-existent attribute or method",
            "index": "List/array index out of bounds",
            "key": "Dictionary key not found",
            "zero_division": "Division by zero in calculation",
            "name": "Variable or function not defined",
            "syntax": "Code has syntax errors",
            "import": "Missing or incorrect imports",
            "logic_error": "Core logic is incorrect",
            "partial_failure": "Some edge cases not handled correctly",
        }
        
        return causes.get(error_type, "Unknown error in implementation")
    
    def _generate_suggestions(self, error_type: str, 
                            test_result: TestResult,
                            code: str = None) -> List[str]:
        """Generate suggested fixes based on error type.
        
        Args:
            error_type: Classified error type
            test_result: Test results
            code: Source code
            
        Returns:
            List of suggested fixes
        """
        suggestions = []
        
        if error_type == "timeout":
            suggestions.extend([
                "Add base case to recursive functions",
                "Replace infinite loops with bounded iterations",
                "Optimize algorithm complexity",
                "Check for infinite recursion"
            ])
        
        elif error_type == "assertion":
            suggestions.extend([
                "Review function logic and return values",
                "Check calculations and formulas",
                "Verify edge case handling",
                "Test with example inputs manually"
            ])
        
        elif error_type == "type":
            suggestions.extend([
                "Add type validation for inputs",
                "Ensure return type matches specification",
                "Check type conversions (int, str, list, etc.)",
                "Add type hints to function signature"
            ])
        
        elif error_type == "index":
            suggestions.extend([
                "Add bounds checking before list access",
                "Verify list is not empty before indexing",
                "Use list.get() for safe access",
                "Check loop ranges and indices"
            ])
        
        elif error_type == "key":
            suggestions.extend([
                "Use dict.get() with default value",
                "Check if key exists before access",
                "Verify dictionary structure",
                "Handle missing keys gracefully"
            ])
        
        elif error_type == "zero_division":
            suggestions.extend([
                "Add check for zero before division",
                "Handle edge case where divisor is zero",
                "Return special value for undefined division"
            ])
        
        elif error_type == "name":
            suggestions.extend([
                "Define all variables before use",
                "Check variable names for typos",
                "Import required modules",
                "Verify function and variable scope"
            ])
        
        elif error_type == "syntax":
            suggestions.extend([
                "Fix syntax errors (colons, parentheses, indentation)",
                "Check for unclosed brackets or quotes",
                "Verify proper indentation",
                "Ensure valid Python syntax"
            ])
        
        elif error_type == "import":
            suggestions.extend([
                "Ensure the function name matches exactly what's imported in tests",
                "Check the function is defined in impl.py",
                "Verify no typos in function name",
                "Make sure the function name matches the specification"
            ])
        
        elif error_type == "partial_failure":
            # Analyze which tests pass/fail
            if test_result.failures:
                failing_names = [f.get("test", "") for f in test_result.failures]
                
                # Check for "raises_error" or "raises" in test names - indicates missing error handling
                if any("raises" in name.lower() for name in failing_names):
                    suggestions.append("Add input validation and raise appropriate exceptions (ValueError, TypeError)")
                    suggestions.append("Check for empty inputs, invalid types, and boundary conditions")
                
                if any("empty" in name.lower() for name in failing_names):
                    suggestions.append("Handle empty input case")
                if any("zero" in name.lower() for name in failing_names):
                    suggestions.append("Handle zero value case")
                if any("negative" in name.lower() for name in failing_names):
                    suggestions.append("Handle negative numbers")
                if any("single" in name.lower() for name in failing_names):
                    suggestions.append("Handle single element case")
                if any("large" in name.lower() for name in failing_names):
                    suggestions.append("Handle large input values")
        
        # Additional check: if "DID NOT RAISE" appears in output, add specific suggestion
        if test_result.stdout and "DID NOT RAISE" in test_result.stdout:
            if not any("validation" in s.lower() for s in suggestions):
                suggestions.insert(0, "CRITICAL: Add input validation - tests expect exceptions to be raised for invalid inputs")
                suggestions.insert(1, "Use isinstance() to check types and raise TypeError for invalid types")
                suggestions.insert(2, "Check input constraints (length, values) and raise ValueError when violated")
        
        if not suggestions:
            suggestions.append("Review implementation against specification")
            suggestions.append("Test with failing test inputs manually")
        
        return suggestions
