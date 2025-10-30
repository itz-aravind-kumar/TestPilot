"""Metrics tracking for Auto-TDD system."""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

from config import Config

@dataclass
class IterationMetrics:
    """Metrics for a single refinement iteration."""
    iteration: int
    timestamp: str
    tests_passed: int
    tests_failed: int
    tests_total: int
    pass_rate: float
    duration: float
    reward: float
    error_type: str
    code_changes: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RunMetrics:
    """Metrics for a complete Auto-TDD run."""
    run_id: str
    start_time: str
    end_time: str
    total_duration: float
    problem_name: str
    function_name: str
    
    # Iteration data
    iterations: List[IterationMetrics]
    final_iteration: int
    converged: bool
    success: bool
    
    # Final results
    final_pass_rate: float
    final_reward: float
    total_tests: int
    
    # Code quality
    code_complexity: int
    code_lines: int
    lint_errors: int
    security_issues: int
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['iterations'] = [iter.to_dict() for iter in self.iterations]
        return data
    
    def save(self, output_dir: Path):
        """Save metrics to JSON file."""
        metrics_file = output_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return f"""
Auto-TDD Run Summary
====================
Run ID: {self.run_id}
Problem: {self.problem_name} ({self.function_name})
Duration: {self.total_duration:.2f}s
Iterations: {self.final_iteration}
Status: {'✓ SUCCESS' if self.success else '✗ FAILED'}

Final Results:
  Pass Rate: {self.final_pass_rate*100:.1f}%
  Tests: {self.total_tests}
  Reward: {self.final_reward:.2f}
  
Code Quality:
  Lines: {self.code_lines}
  Complexity: {self.code_complexity}
  Lint Errors: {self.lint_errors}
  Security Issues: {self.security_issues}
"""

class MetricsCollector:
    """Collects and manages metrics during Auto-TDD execution."""
    
    def __init__(self, run_id: str, problem_name: str, function_name: str):
        self.run_id = run_id
        self.problem_name = problem_name
        self.function_name = function_name
        self.start_time = datetime.now()
        self.iterations: List[IterationMetrics] = []
        
    def add_iteration(self, iteration: int, test_result: Any,
                     reward: float, error_type: str,
                     duration: float, code_changes: int = 0):
        """Add metrics for an iteration."""
        metrics = IterationMetrics(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            tests_passed=test_result.passed,
            tests_failed=test_result.failed,
            tests_total=test_result.total,
            pass_rate=test_result.passed / test_result.total if test_result.total > 0 else 0.0,
            duration=duration,
            reward=reward,
            error_type=error_type,
            code_changes=code_changes
        )
        self.iterations.append(metrics)
    
    def finalize(self, success: bool, converged: bool,
                code_quality: Dict[str, Any]) -> RunMetrics:
        """Finalize metrics and create RunMetrics object."""
        end_time = datetime.now()
        
        final_iter = self.iterations[-1] if self.iterations else None
        
        metrics = RunMetrics(
            run_id=self.run_id,
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration=(end_time - self.start_time).total_seconds(),
            problem_name=self.problem_name,
            function_name=self.function_name,
            iterations=self.iterations,
            final_iteration=len(self.iterations),
            converged=converged,
            success=success,
            final_pass_rate=final_iter.pass_rate if final_iter else 0.0,
            final_reward=final_iter.reward if final_iter else 0.0,
            total_tests=final_iter.tests_total if final_iter else 0,
            code_complexity=code_quality.get('complexity', 0),
            code_lines=code_quality.get('lines', 0),
            lint_errors=code_quality.get('lint_errors', 0),
            security_issues=code_quality.get('security_issues', 0)
        )
        
        return metrics
