"""Refinement Loop Module with RL-based rewards."""
import time
from typing import Tuple, Optional, List
from dataclasses import dataclass

from parser import ProblemSpec
from sandbox_runner import SandboxRunner, TestResult
from failure_analyzer import FailureAnalyzer, FailureAnalysis
from code_generator import CodeGenerator
from logger import logger
from config import Config
from metrics import MetricsCollector

@dataclass
class RewardState:
    """State information for RL reward calculation."""
    test_result: TestResult
    code: str
    iteration: int
    prev_pass_rate: float
    execution_time: float
    code_quality: dict
    
class RewardCalculator:
    """Calculates RL-style rewards for code generation iterations."""
    
    def __init__(self):
        self.history = []
    
    def calculate_reward(self, state: RewardState) -> float:
        """Calculate reward for current state using RL principles.
        
        Reward Components:
        1. Test passing reward (primary signal)
        2. Improvement bonus (delta from previous iteration)
        3. Quality bonus (clean, efficient code)
        4. Penalties for errors and timeouts
        
        Args:
            state: Current state information
            
        Returns:
            Total reward value
        """
        reward = 0.0
        
        # 1. Base reward from test results
        pass_rate = state.test_result.passed / max(state.test_result.total, 1)
        reward += pass_rate * Config.REWARD_TEST_PASS
        
        # 2. Improvement reward (compared to previous iteration)
        if state.prev_pass_rate is not None:
            improvement = pass_rate - state.prev_pass_rate
            if improvement > 0:
                reward += improvement * Config.REWARD_EFFICIENCY_BONUS * 2
            elif improvement < 0:
                # Regression penalty
                reward += improvement * 10  # Negative reward
        
        # 3. Quality bonuses
        if state.code_quality:
            # Low complexity bonus
            complexity = state.code_quality.get('complexity', 10)
            if complexity < 5:
                reward += Config.REWARD_QUALITY_BONUS * 0.5
            elif complexity < 10:
                reward += Config.REWARD_QUALITY_BONUS * 0.25
            
            # No lint errors bonus
            if state.code_quality.get('lint_errors', 0) == 0:
                reward += Config.REWARD_QUALITY_BONUS * 0.3
            
            # No security issues bonus
            if state.code_quality.get('security_issues', 0) == 0:
                reward += Config.REWARD_QUALITY_BONUS * 0.2
        
        # 4. Efficiency bonus (fast execution)
        if state.execution_time < 1.0:
            reward += Config.REWARD_EFFICIENCY_BONUS
        elif state.execution_time < 3.0:
            reward += Config.REWARD_EFFICIENCY_BONUS * 0.5
        
        # 5. Penalties
        if state.test_result.timed_out:
            reward += Config.PENALTY_TIMEOUT
        
        if state.test_result.errors > 0:
            reward += Config.PENALTY_RUNTIME_ERROR * state.test_result.errors
        
        # Syntax penalty (from quality)
        if state.code_quality.get('syntax_error', False):
            reward += Config.PENALTY_SYNTAX_ERROR
        
        # 6. Convergence bonus (all tests pass)
        if pass_rate == 1.0:
            reward += Config.REWARD_TEST_PASS * 2  # Double reward for perfect score
        
        # Store for analysis
        self.history.append({
            'iteration': state.iteration,
            'reward': reward,
            'pass_rate': pass_rate,
            'components': {
                'base': pass_rate * Config.REWARD_TEST_PASS,
                'quality': reward - (pass_rate * Config.REWARD_TEST_PASS)
            }
        })
        
        logger.debug("Reward calculated",
                    iteration=state.iteration,
                    reward=round(reward, 2),
                    pass_rate=round(pass_rate, 3))
        
        return reward

class RefinementLoop:
    """Iterative refinement loop with RL-based optimization."""
    
    def __init__(self):
        self.sandbox = SandboxRunner()
        self.analyzer = FailureAnalyzer()
        self.generator = CodeGenerator()
        self.reward_calculator = RewardCalculator()
        self.max_iterations = Config.MAX_ITERATIONS
        self.convergence_patience = Config.CONVERGENCE_PATIENCE
    
    def refine(self, spec: ProblemSpec, initial_code: str, 
               test_code: str) -> Tuple[str, dict]:
        """Iteratively refine code until tests pass or max iterations reached.
        
        Args:
            spec: Problem specification
            initial_code: Initial generated code
            test_code: Test suite code
            
        Returns:
            Tuple of (final_code, refinement_metadata)
        """
        logger.info("Starting refinement loop",
                   max_iterations=self.max_iterations)
        
        code = initial_code
        prev_pass_rate = 0.0
        no_improvement_count = 0
        best_code = code
        best_reward = float('-inf')
        best_iteration = 0
        best_code_pass_rate = 0.0  # Track pass rate of best code
        
        metadata = {
            'iterations': [],
            'converged': False,
            'final_reward': 0.0,
            'best_iteration': 0,
            'improvement_history': []
        }
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Refinement iteration {iteration}/{self.max_iterations}")
            
            start_time = time.time()
            
            # Run tests in sandbox
            test_result = self.sandbox.run_tests(code, test_code)
            
            execution_time = time.time() - start_time
            
            # Analyze code quality
            from quality_checks import QualityChecker
            quality_checker = QualityChecker()
            quality_result = quality_checker.check(code)
            
            # Calculate reward
            reward_state = RewardState(
                test_result=test_result,
                code=code,
                iteration=iteration,
                prev_pass_rate=prev_pass_rate,
                execution_time=execution_time,
                code_quality=quality_result
            )
            
            reward = self.reward_calculator.calculate_reward(reward_state)
            
            # Calculate pass rate for this iteration
            pass_rate = test_result.passed / max(test_result.total, 1)
            
            # Track best solution based on PASS RATE first, then reward
            # This ensures we always pick the solution with most tests passing
            is_better = False
            if pass_rate > (best_code_pass_rate if best_iteration > 0 else 0):
                # Better pass rate - always prefer
                is_better = True
            elif pass_rate == (best_code_pass_rate if best_iteration > 0 else 0) and reward > best_reward:
                # Same pass rate, higher reward - prefer
                is_better = True
            
            if is_better:
                best_reward = reward
                best_code = code
                best_iteration = iteration
                best_code_pass_rate = pass_rate
                no_improvement_count = 0
                logger.info(f"[NEW BEST] Solution found at iteration {iteration}",
                          reward=round(reward, 2),
                          pass_rate=round(pass_rate, 3),
                          tests_passed=test_result.passed)
            else:
                no_improvement_count += 1
            
            # Store iteration metrics
            metadata['iterations'].append({
                'iteration': iteration,
                'passed': test_result.passed,
                'failed': test_result.failed,
                'total': test_result.total,
                'pass_rate': pass_rate,
                'reward': reward,
                'duration': execution_time
            })
            
            logger.info(f"Iteration {iteration} results",
                       passed=test_result.passed,
                       failed=test_result.failed,
                       reward=round(reward, 2),
                       pass_rate=round(pass_rate, 3))
            
            # Check convergence (all tests pass)
            if test_result.failed == 0 and test_result.errors == 0 and test_result.passed > 0:
                logger.info("[SUCCESS] All tests passed! Refinement converged.",
                           iterations=iteration)
                metadata['converged'] = True
                metadata['final_reward'] = reward
                return code, metadata
            
            # Check for stagnation
            if no_improvement_count >= self.convergence_patience:
                logger.warning("No improvement for multiple iterations, stopping",
                             patience=self.convergence_patience)
                break
            
            # Check minimal improvement
            improvement = pass_rate - prev_pass_rate
            if iteration > 2 and abs(improvement) < Config.MIN_IMPROVEMENT_THRESHOLD:
                logger.warning("Minimal improvement detected",
                             improvement=improvement)
                if no_improvement_count >= 1:
                    break
            
            # Analyze failures
            analysis = self.analyzer.analyze(test_result, code)
            feedback = analysis.to_feedback()
            
            logger.info("Failure analysis",
                       error_type=analysis.error_type,
                       failing_tests=len(analysis.failing_tests))
            
            # DEBUG: Log full feedback being sent to LLM
            logger.debug("Feedback for refinement",
                        feedback_length=len(feedback),
                        feedback_preview=feedback[:500] if len(feedback) > 500 else feedback)
            
            # DEBUG: Log code when syntax error occurs
            if analysis.error_type == "syntax":
                logger.error("SYNTAX ERROR in generated code",
                            code_preview=code[:500],
                            feedback=feedback[:300])
            
            # Generate refined code
            try:
                refined_code, gen_metadata = self.generator.generate(
                    spec,
                    test_code,
                    feedback
                )
                
                # Validate refinement
                from utils import validate_python_syntax
                is_valid, error = validate_python_syntax(refined_code)
                
                if not is_valid:
                    logger.error("Refined code has syntax errors",
                               error=error)
                    # Keep previous code
                    refined_code = code
                
                code = refined_code
                prev_pass_rate = pass_rate
                
            except Exception as e:
                logger.error("Code refinement failed", error=str(e))
                break
        
        # Return best solution found
        logger.info("Refinement loop completed",
                   final_iterations=iteration,
                   best_iteration=best_iteration,
                   best_reward=round(best_reward, 2),
                   converged=metadata['converged'])
        
        metadata['final_reward'] = best_reward
        metadata['best_iteration'] = best_iteration
        
        return best_code, metadata
    
    def cleanup(self):
        """Clean up resources."""
        if self.sandbox:
            self.sandbox.cleanup()
