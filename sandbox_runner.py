"""Sandboxed Runner Module - Executes code in isolated Docker containers."""
import docker
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
import time

from logger import logger
from config import Config

class TestResult:
    """Container for test execution results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.total = 0
        self.duration = 0.0
        self.failures = []
        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0
        self.timed_out = False
        self.coverage = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "total": self.total,
            "duration": self.duration,
            "failures": self.failures,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "coverage": self.coverage,
            "pass_rate": self.passed / self.total if self.total > 0 else 0.0
        }

class SandboxRunner:
    """Executes code and tests in sandboxed Docker containers."""
    
    def __init__(self):
        self.docker_client = None
        self._initialize_docker()
    
    def _initialize_docker(self):
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Docker", error=str(e))
            raise RuntimeError(f"Docker initialization failed: {e}")
    
    def run_tests(self, code: str, test_code: str, 
                  timeout: int = None) -> TestResult:
        """Run tests in sandboxed environment.
        
        Args:
            code: Implementation code
            test_code: Test code
            timeout: Execution timeout in seconds
            
        Returns:
            TestResult object with execution results
        """
        timeout = timeout or Config.EXECUTION_TIMEOUT
        
        logger.info("Running tests in sandbox", timeout=timeout)
        
        result = TestResult()
        start_time = time.time()
        
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write code files
            impl_file = temp_path / "impl.py"
            test_file = temp_path / "test_impl.py"
            requirements_file = temp_path / "requirements.txt"
            
            # DEBUG: Log what we're writing
            logger.debug("Writing impl.py",
                        code_length=len(code),
                        first_line=code.split('\n')[0] if code else "EMPTY",
                        has_def=("def " in code))
            
            # ALWAYS save code for debugging
            debug_file = Config.LOGS_DIR / "last_generated_impl.py"
            debug_file.write_text(code, encoding='utf-8')
            logger.info(f"Generated code saved to {debug_file}")
            
            debug_test_file = Config.LOGS_DIR / "last_generated_test.py"
            debug_test_file.write_text(test_code, encoding='utf-8')
            logger.info(f"Generated tests saved to {debug_test_file}")
            
            # Quick syntax check before writing
            try:
                compile(code, '<string>', 'exec')
                logger.debug("Code syntax is valid")
            except SyntaxError as e:
                logger.error("SYNTAX ERROR before writing to file",
                            error=str(e),
                            line=e.lineno,
                            offset=e.offset,
                            text=e.text)
                # Save problematic code for debugging to logs folder
                error_file = Config.LOGS_DIR / "last_syntax_error.py"
                error_file.write_text(f"# SYNTAX ERROR at line {e.lineno}\n# {e.msg}\n\n{code}", encoding='utf-8')
                logger.error(f"Problematic code saved to {error_file}")
            
            impl_file.write_text(code, encoding='utf-8')
            test_file.write_text(test_code, encoding='utf-8')
            requirements_file.write_text("pytest\nhypothesis\n", encoding='utf-8')
            
            try:
                # Run in Docker container
                container_result = self._run_in_container(
                    temp_path, 
                    timeout
                )
                
                result.stdout = container_result.get("stdout", "")
                result.stderr = container_result.get("stderr", "")
                result.exit_code = container_result.get("exit_code", 1)
                result.timed_out = container_result.get("timed_out", False)
                
                # Parse pytest output
                self._parse_pytest_output(result)
                
            except Exception as e:
                logger.error("Sandbox execution failed", error=str(e))
                result.errors = 1
                result.stderr = str(e)
                result.exit_code = 1
        
        result.duration = time.time() - start_time
        
        logger.info("Test execution completed",
                   passed=result.passed,
                   failed=result.failed,
                   duration=result.duration)
        
        return result
    
    def _run_in_container(self, code_dir: Path, 
                         timeout: int) -> Dict[str, Any]:
        """Execute code in Docker container with security restrictions.
        
        Args:
            code_dir: Directory containing code files
            timeout: Execution timeout
            
        Returns:
            Dictionary with stdout, stderr, exit_code, timed_out
        """
        try:
            # Pull image if not present
            try:
                self.docker_client.images.get(Config.DOCKER_IMAGE)
            except docker.errors.ImageNotFound:
                logger.info("Pulling Docker image", image=Config.DOCKER_IMAGE)
                self.docker_client.images.pull(Config.DOCKER_IMAGE)
            
            # Run container with restrictions
            logger.info("[SANDBOX] Creating isolated Docker container", 
                       image=Config.DOCKER_IMAGE,
                       memory_limit=Config.MAX_MEMORY,
                       cpu_quota=f"{Config.CPU_QUOTA/1000}%",
                       network="disabled",
                       filesystem="read-only")
            
            container = self.docker_client.containers.run(
                image=Config.DOCKER_IMAGE,
                command=[
                    "/bin/sh", "-c",
                    "pytest test_impl.py -v --tb=short --no-header"
                ],
                volumes={
                    str(code_dir.absolute()): {
                        'bind': '/workspace',
                        'mode': 'ro'  # Read-only
                    }
                },
                working_dir='/workspace',
                mem_limit=Config.MAX_MEMORY,
                cpu_quota=Config.CPU_QUOTA,
                network_disabled=Config.NETWORK_DISABLED,
                detach=True,
                environment={
                    'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'
                }
            )
            
            logger.info("[SANDBOX] Container started", 
                       container_id=container.short_id,
                       status="running")
            
            # Wait for completion with timeout
            try:
                logger.info("[SANDBOX] Executing tests...", container_id=container.short_id)
                result_code = container.wait(timeout=timeout)
                
                # Get exit code value
                if isinstance(result_code, dict):
                    exit_code = result_code.get('StatusCode', 1)
                else:
                    exit_code = result_code
                
                # Get logs BEFORE removing container
                stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
                stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
                
                logger.info("[SANDBOX] Tests completed", 
                           container_id=container.short_id,
                           exit_code=exit_code)
                
                # Clean up container
                container.remove()
                logger.info("[SANDBOX] Container destroyed", container_id=container.short_id)
                
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "timed_out": False
                }
                
            except Exception as e:
                # Timeout or other error
                try:
                    container.kill()
                except:
                    pass
                
                logger.warning("Container execution timeout or error", error=str(e))
                
                return {
                    "stdout": "",
                    "stderr": f"Execution timeout or error: {str(e)}",
                    "exit_code": 124,
                    "timed_out": True
                }
                
        except Exception as e:
            logger.error("Container execution failed", error=str(e))
            return {
                "stdout": "",
                "stderr": f"Container error: {str(e)}",
                "exit_code": 1,
                "timed_out": False
            }
    
    def _parse_pytest_output(self, result: TestResult):
        """Parse pytest output to extract test results.
        
        Args:
            result: TestResult object to populate
        """
        output = result.stdout + result.stderr
        
        # Parse test counts
        # Look for patterns like: "5 passed, 2 failed, 1 error in 0.42s"
        import re
        
        # Passed tests
        passed_match = re.search(r'(\d+) passed', output)
        if passed_match:
            result.passed = int(passed_match.group(1))
        
        # Failed tests
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            result.failed = int(failed_match.group(1))
        
        # Errors
        error_match = re.search(r'(\d+) error', output)
        if error_match:
            result.errors = int(error_match.group(1))
        
        # Skipped
        skipped_match = re.search(r'(\d+) skipped', output)
        if skipped_match:
            result.skipped = int(skipped_match.group(1))
        
        result.total = result.passed + result.failed + result.errors + result.skipped
        
        # Extract failure details
        # Look for FAILED test_impl.py::test_name or just test_name
        # Pattern matches: "FAILED test_impl.py::test_function_name"
        failure_pattern = r'FAILED\s+(?:[\w\./]+::)?(test_\w+)'
        failures = re.finditer(failure_pattern, output)
        
        for match in failures:
            test_name = match.group(1)
            
            # Try to extract error message after the test name
            # Look for the section after this test failure
            test_pos = match.end()
            next_section = output[test_pos:test_pos + 1000]  # Look ahead 1000 chars
            
            # Extract first line that looks like an error
            error_lines = []
            for line in next_section.split('\n'):
                if any(keyword in line for keyword in ['AssertionError', 'Error:', 'Expected', 'assert', 'FAILED']):
                    error_lines.append(line.strip())
                    if len(error_lines) >= 3:  # Get up to 3 lines of error context
                        break
            
            error_msg = ' '.join(error_lines) if error_lines else "Test failed"
            
            result.failures.append({
                "test": test_name,
                "message": error_msg[:500]  # Limit length
            })
        
        # DEBUG: Log if we have failed tests but no failure details
        if result.failed > 0 and len(result.failures) == 0:
            logger.warning("Failed to extract failure details",
                          failed_count=result.failed,
                          output_preview=output[:1000])
        
        # If exit code is 0 but no passed tests found, might be all passed
        if result.exit_code == 0 and result.passed == 0 and result.total == 0:
            # Try to count test functions
            test_count = output.count("PASSED")
            if test_count > 0:
                result.passed = test_count
                result.total = test_count
    
    def cleanup(self):
        """Clean up Docker resources."""
        if self.docker_client:
            try:
                # Remove dangling containers
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={"status": "exited"}
                )
                for container in containers[:10]:  # Limit cleanup
                    try:
                        container.remove()
                    except:
                        pass
            except Exception as e:
                logger.warning("Cleanup failed", error=str(e))
