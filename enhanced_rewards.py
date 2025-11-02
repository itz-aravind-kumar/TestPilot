"""Enhanced Reward System with Multi-Dimensional Scoring."""
import ast
import re
from typing import Dict, Any, List, Tuple, Optional
import Levenshtein
from radon.complexity import cc_visit
from radon.metrics import mi_visit

from logger import logger


class PartialCorrectnessCalculator:
    """Calculates partial correctness rewards for near-miss test failures."""
    
    @staticmethod
    def calculate(test_result, max_reward: float = 15.0) -> Tuple[float, Dict[str, Any]]:
        """Calculate partial correctness reward from test failures.
        
        Args:
            test_result: TestResult object with failure information
            max_reward: Maximum partial correctness reward
            
        Returns:
            Tuple of (reward, breakdown_dict)
        """
        if test_result.failed == 0:
            # All tests passed, no partial credit needed
            return 0.0, {'note': 'All tests passed'}
        
        total_similarity = 0.0
        similarity_count = 0
        breakdown = {
            'string_similarities': [],
            'numeric_closeness': [],
            'type_matches': 0,
            'total_failures': test_result.failed
        }
        
        for failure in test_result.failures:
            message = failure.get('message', '')
            
            # Extract expected vs actual from assertion errors
            expected, actual = PartialCorrectnessCalculator._extract_values(message)
            
            if expected is not None and actual is not None:
                similarity = PartialCorrectnessCalculator._calculate_similarity(
                    expected, actual
                )
                
                if similarity > 0:
                    total_similarity += similarity
                    similarity_count += 1
                    
                    breakdown['string_similarities'].append({
                        'expected': str(expected)[:50],
                        'actual': str(actual)[:50],
                        'similarity': round(similarity, 3)
                    })
        
        # Calculate average similarity across failures
        if similarity_count > 0:
            avg_similarity = total_similarity / similarity_count
            reward = avg_similarity * max_reward
            breakdown['average_similarity'] = round(avg_similarity, 3)
            breakdown['similarity_count'] = similarity_count
        else:
            reward = 0.0
            breakdown['note'] = 'No parseable expected/actual values'
        
        logger.debug("Partial correctness calculated",
                    reward=round(reward, 2),
                    avg_similarity=breakdown.get('average_similarity', 0))
        
        return reward, breakdown
    
    @staticmethod
    def _extract_values(message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract expected and actual values from error message.
        
        Returns:
            Tuple of (expected, actual) or (None, None) if not found
        """
        # Pattern 1: "Expected X but got Y" or "Expected: X | Actual: Y"
        pattern1 = r'Expected[:\s]+(.+?)[\s|]+(?:but got|Actual:)\s+(.+?)(?:\n|$)'
        match = re.search(pattern1, message, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Pattern 2: "assert X == Y" where X failed
        pattern2 = r'assert\s+(.+?)\s*==\s*(.+?)(?:\n|$)'
        match = re.search(pattern2, message)
        if match:
            return match.group(2).strip(), match.group(1).strip()
        
        # Pattern 3: Direct comparison in message
        pattern3 = r'(\d+(?:\.\d+)?)\s*!=\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern3, message)
        if match:
            return match.group(1), match.group(2)
        
        return None, None
    
    @staticmethod
    def _calculate_similarity(expected: str, actual: str) -> float:
        """Calculate similarity between expected and actual values.
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Try numeric comparison first
        try:
            exp_num = float(expected)
            act_num = float(actual)
            
            # Calculate relative error
            if exp_num == 0:
                if act_num == 0:
                    return 1.0
                else:
                    return 0.0
            
            relative_error = abs(exp_num - act_num) / abs(exp_num)
            similarity = max(0.0, 1.0 - relative_error)
            return similarity
            
        except (ValueError, TypeError):
            pass
        
        # String similarity using Levenshtein distance
        expected_str = str(expected).lower()
        actual_str = str(actual).lower()
        
        if len(expected_str) == 0 and len(actual_str) == 0:
            return 1.0
        if len(expected_str) == 0 or len(actual_str) == 0:
            return 0.0
        
        # Normalized Levenshtein similarity
        distance = Levenshtein.distance(expected_str, actual_str)
        max_len = max(len(expected_str), len(actual_str))
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)


class CodeQualityCalculator:
    """Calculates code quality rewards based on Pythonic patterns and structure."""
    
    @staticmethod
    def calculate(code: str, max_reward: float = 10.0) -> Tuple[float, Dict[str, Any]]:
        """Calculate code quality reward.
        
        Args:
            code: Source code to analyze
            max_reward: Maximum quality reward
            
        Returns:
            Tuple of (reward, breakdown_dict)
        """
        reward = 0.0
        breakdown = {
            'complexity_score': 0.0,
            'pythonic_patterns': [],
            'code_smells': [],
            'has_docstring': False,
            'has_type_hints': False
        }
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            breakdown['note'] = 'Syntax error in code'
            return 0.0, breakdown
        
        # 1. Complexity scoring (40% of quality reward)
        complexity_reward = CodeQualityCalculator._calculate_complexity_reward(code)
        reward += complexity_reward * 0.4 * max_reward
        breakdown['complexity_score'] = round(complexity_reward, 3)
        
        # 2. Pythonic patterns detection (30% of quality reward)
        pythonic_reward, patterns = CodeQualityCalculator._detect_pythonic_patterns(tree)
        reward += pythonic_reward * 0.3 * max_reward
        breakdown['pythonic_patterns'] = patterns
        
        # 3. Code smell penalties (20% of quality reward)
        smell_penalty, smells = CodeQualityCalculator._detect_code_smells(tree, code)
        reward += smell_penalty * 0.2 * max_reward
        breakdown['code_smells'] = smells
        
        # 4. Documentation bonus (10% of quality reward)
        doc_reward = CodeQualityCalculator._check_documentation(tree)
        reward += doc_reward * 0.1 * max_reward
        breakdown['has_docstring'] = doc_reward > 0
        
        logger.debug("Code quality calculated",
                    reward=round(reward, 2),
                    complexity=breakdown['complexity_score'])
        
        return reward, breakdown
    
    @staticmethod
    def _calculate_complexity_reward(code: str) -> float:
        """Calculate reward based on cyclomatic complexity.
        
        Lower complexity = higher reward.
        Returns value between 0.0 and 1.0.
        """
        try:
            complexity_scores = cc_visit(code)
            if not complexity_scores:
                return 0.5  # Neutral score
            
            avg_complexity = sum(c.complexity for c in complexity_scores) / len(complexity_scores)
            
            # Scoring: complexity < 5 = 1.0, complexity > 15 = 0.0
            if avg_complexity <= 5:
                return 1.0
            elif avg_complexity >= 15:
                return 0.0
            else:
                return 1.0 - ((avg_complexity - 5) / 10)
                
        except Exception as e:
            logger.debug("Complexity calculation failed", error=str(e))
            return 0.5
    
    @staticmethod
    def _detect_pythonic_patterns(tree: ast.AST) -> Tuple[float, List[str]]:
        """Detect Pythonic coding patterns.
        
        Returns:
            Tuple of (score, list_of_patterns_found)
        """
        patterns = []
        score = 0.0
        
        for node in ast.walk(tree):
            # List comprehensions
            if isinstance(node, ast.ListComp):
                patterns.append('list_comprehension')
                score += 0.1
            
            # Dict comprehensions
            elif isinstance(node, ast.DictComp):
                patterns.append('dict_comprehension')
                score += 0.1
            
            # Context managers (with statement)
            elif isinstance(node, ast.With):
                patterns.append('context_manager')
                score += 0.15
            
            # Generator expressions
            elif isinstance(node, ast.GeneratorExp):
                patterns.append('generator_expression')
                score += 0.1
            
            # f-strings (Python 3.6+)
            elif isinstance(node, ast.JoinedStr):
                patterns.append('f_string')
                score += 0.05
        
        return min(1.0, score), patterns
    
    @staticmethod
    def _detect_code_smells(tree: ast.AST, code: str) -> Tuple[float, List[str]]:
        """Detect code smells and anti-patterns.
        
        Returns:
            Tuple of (penalty_score, list_of_smells) - negative score for penalties
        """
        smells = []
        penalty = 0.0
        
        for node in ast.walk(tree):
            # Bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    smells.append('bare_except')
                    penalty -= 0.2
            
            # Global statements
            elif isinstance(node, ast.Global):
                smells.append('global_statement')
                penalty -= 0.15
            
            # Overly long functions (> 50 lines)
            elif isinstance(node, ast.FunctionDef):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        smells.append(f'long_function_{node.name}')
                        penalty -= 0.1
        
        # Check for magic numbers in code
        if re.search(r'\b\d{3,}\b', code):  # Numbers with 3+ digits
            smells.append('magic_numbers')
            penalty -= 0.05
        
        return max(-1.0, penalty), smells
    
    @staticmethod
    def _check_documentation(tree: ast.AST) -> float:
        """Check for docstrings and documentation.
        
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if docstring and len(docstring) > 10:
                    score += 0.3
        
        return min(1.0, score)


class EfficiencyCalculator:
    """Calculates efficiency rewards based on execution time and complexity."""
    
    @staticmethod
    def calculate(execution_time: float, code: str, 
                  max_reward: float = 10.0) -> Tuple[float, Dict[str, Any]]:
        """Calculate efficiency reward.
        
        Args:
            execution_time: Time taken to execute tests (seconds)
            code: Source code for complexity analysis
            max_reward: Maximum efficiency reward
            
        Returns:
            Tuple of (reward, breakdown_dict)
        """
        reward = 0.0
        breakdown = {
            'execution_time': round(execution_time, 3),
            'time_score': 0.0,
            'estimated_complexity': 'unknown'
        }
        
        # 1. Time-based reward (70% of efficiency reward)
        # Use logarithmic scaling: fast execution gets high reward
        if execution_time < 0.5:
            time_score = 1.0
        elif execution_time < 1.0:
            time_score = 0.8
        elif execution_time < 2.0:
            time_score = 0.6
        elif execution_time < 5.0:
            time_score = 0.4
        elif execution_time < 10.0:
            time_score = 0.2
        else:
            time_score = 0.1
        
        reward += time_score * 0.7 * max_reward
        breakdown['time_score'] = round(time_score, 3)
        
        # 2. Estimated Big-O complexity (30% of efficiency reward)
        complexity_class = EfficiencyCalculator._estimate_complexity(code)
        breakdown['estimated_complexity'] = complexity_class
        
        complexity_scores = {
            'O(1)': 1.0,
            'O(log n)': 0.9,
            'O(n)': 0.8,
            'O(n log n)': 0.6,
            'O(n^2)': 0.4,
            'O(n^3)': 0.2,
            'O(2^n)': 0.1,
            'unknown': 0.5
        }
        
        complexity_reward = complexity_scores.get(complexity_class, 0.5)
        reward += complexity_reward * 0.3 * max_reward
        
        logger.debug("Efficiency calculated",
                    reward=round(reward, 2),
                    time=execution_time,
                    complexity=complexity_class)
        
        return reward, breakdown
    
    @staticmethod
    def _estimate_complexity(code: str) -> str:
        """Estimate Big-O complexity from code structure.
        
        Returns:
            Complexity class string (e.g., 'O(n)', 'O(n^2)')
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 'unknown'
        
        max_loop_depth = 0
        has_recursion = False
        recursive_calls = set()
        
        # Find all function definitions
        functions = {node.name for node in ast.walk(tree) 
                    if isinstance(node, ast.FunctionDef)}
        
        for node in ast.walk(tree):
            # Check for nested loops
            if isinstance(node, (ast.For, ast.While)):
                depth = EfficiencyCalculator._count_loop_depth(node)
                max_loop_depth = max(max_loop_depth, depth)
            
            # Check for recursion
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            if child.func.id == node.name:
                                has_recursion = True
                                recursive_calls.add(node.name)
        
        # Estimate complexity based on patterns
        if has_recursion:
            # Recursive algorithms - could be O(2^n) or better
            if 'fibonacci' in code.lower() and 'memo' not in code.lower():
                return 'O(2^n)'
            else:
                return 'O(n)'  # Assume memoized or tail-recursive
        
        if max_loop_depth >= 3:
            return 'O(n^3)'
        elif max_loop_depth == 2:
            return 'O(n^2)'
        elif max_loop_depth == 1:
            # Check for log patterns
            if 'log' in code.lower() or '/= 2' in code or '// 2' in code:
                return 'O(n log n)'
            return 'O(n)'
        else:
            # No loops - might be O(1) or O(log n)
            if 'while' in code.lower() and '//' in code:
                return 'O(log n)'
            return 'O(1)'
    
    @staticmethod
    def _count_loop_depth(node: ast.AST, current_depth: int = 1) -> int:
        """Recursively count nested loop depth."""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = EfficiencyCalculator._count_loop_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth


class EnhancedRewardCalculator:
    """Composite reward calculator with multiple dimensions."""
    
    def __init__(self):
        self.history = []
        self.partial_calc = PartialCorrectnessCalculator()
        self.quality_calc = CodeQualityCalculator()
        self.efficiency_calc = EfficiencyCalculator()
    
    def calculate_composite_reward(self, test_result, code: str, 
                                   iteration: int, prev_pass_rate: float,
                                   execution_time: float,
                                   code_quality: dict) -> Tuple[float, Dict[str, Any]]:
        """Calculate composite reward with breakdown.
        
        Returns:
            Tuple of (total_reward, breakdown_dict)
        """
        breakdown = {
            'iteration': iteration,
            'dimensions': {}
        }
        
        total_reward = 0.0
        
        # 1. Test Pass Reward (50% weight) - PRIMARY SIGNAL
        pass_rate = test_result.passed / max(test_result.total, 1)
        test_reward = pass_rate * 50.0  # Base: 50 points max
        total_reward += test_reward
        breakdown['dimensions']['test_passing'] = {
            'reward': round(test_reward, 2),
            'pass_rate': round(pass_rate, 3),
            'passed': test_result.passed,
            'total': test_result.total
        }
        
        # 2. Partial Correctness Reward (15% weight)
        partial_reward, partial_breakdown = self.partial_calc.calculate(test_result, max_reward=15.0)
        total_reward += partial_reward
        breakdown['dimensions']['partial_correctness'] = {
            'reward': round(partial_reward, 2),
            **partial_breakdown
        }
        
        # 3. Code Quality Reward (10% weight)
        quality_reward, quality_breakdown = self.quality_calc.calculate(code, max_reward=10.0)
        total_reward += quality_reward
        breakdown['dimensions']['code_quality'] = {
            'reward': round(quality_reward, 2),
            **quality_breakdown
        }
        
        # 4. Efficiency Reward (10% weight)
        efficiency_reward, efficiency_breakdown = self.efficiency_calc.calculate(
            execution_time, code, max_reward=10.0
        )
        total_reward += efficiency_reward
        breakdown['dimensions']['efficiency'] = {
            'reward': round(efficiency_reward, 2),
            **efficiency_breakdown
        }
        
        # 5. Improvement Bonus (10% weight)
        improvement_reward = 0.0
        if prev_pass_rate is not None:
            improvement = pass_rate - prev_pass_rate
            if improvement > 0:
                improvement_reward = improvement * 10.0
                total_reward += improvement_reward
        
        breakdown['dimensions']['improvement'] = {
            'reward': round(improvement_reward, 2),
            'prev_pass_rate': prev_pass_rate,
            'improvement': round(pass_rate - prev_pass_rate, 3) if prev_pass_rate is not None else 0
        }
        
        # 6. Convergence Bonus (5% weight)
        convergence_reward = 0.0
        if pass_rate == 1.0:
            convergence_reward = 5.0
            total_reward += convergence_reward
        
        breakdown['dimensions']['convergence'] = {
            'reward': round(convergence_reward, 2),
            'all_passed': pass_rate == 1.0
        }
        
        # Apply penalties
        penalties = 0.0
        if test_result.timed_out:
            penalties -= 8.0
        if test_result.errors > 0:
            penalties -= 3.0 * test_result.errors
        if code_quality.get('syntax_error', False):
            penalties -= 5.0
        
        total_reward += penalties
        breakdown['penalties'] = round(penalties, 2)
        breakdown['total_reward'] = round(total_reward, 2)
        
        # Store history
        self.history.append(breakdown)
        
        logger.info("Enhanced reward calculated",
                   total=round(total_reward, 2),
                   test=round(test_reward, 2),
                   partial=round(partial_reward, 2),
                   quality=round(quality_reward, 2),
                   efficiency=round(efficiency_reward, 2))
        
        return total_reward, breakdown
