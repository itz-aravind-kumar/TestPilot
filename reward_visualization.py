"""Visualization utilities for Gradio UI."""
import json
from typing import Dict, List, Any


def format_reward_breakdown(metadata: Dict[str, Any]) -> str:
    """Format reward breakdown for display in Gradio.
    
    Args:
        metadata: Refinement metadata containing iterations with reward breakdowns
        
    Returns:
        Formatted markdown string with reward visualizations
    """
    if 'iterations' not in metadata or len(metadata['iterations']) == 0:
        return "No reward data available."
    
    output = []
    output.append("# 🎯 Reward Evolution\n")
    
    # Overall summary
    final_iter = metadata['iterations'][-1]
    best_iter = metadata.get('best_iteration', len(metadata['iterations']))
    
    output.append("## Summary\n")
    output.append(f"- **Best Iteration**: {best_iter}")
    output.append(f"- **Total Iterations**: {len(metadata['iterations'])}")
    output.append(f"- **Converged**: {'✅ Yes' if metadata.get('converged', False) else '❌ No'}")
    output.append(f"- **Final Reward**: {metadata.get('final_reward', 0):.2f}\n")
    
    # Iteration-by-iteration breakdown
    output.append("## Iteration Details\n")
    
    for iter_data in metadata['iterations']:
        iteration = iter_data['iteration']
        is_best = (iteration == best_iter)
        
        # Header
        marker = "⭐ BEST" if is_best else ""
        output.append(f"### Iteration {iteration} {marker}\n")
        
        # Test results
        passed = iter_data['passed']
        total = iter_data['total']
        pass_rate = iter_data['pass_rate']
        
        output.append(f"**Tests**: {passed}/{total} passed ({pass_rate:.1%})\n")
        
        # Reward breakdown (if available)
        if 'reward_breakdown' in iter_data:
            breakdown = iter_data['reward_breakdown']
            total_reward = breakdown.get('total_reward', 0)
            
            output.append(f"**Total Reward**: {total_reward:.2f}/100.0\n")
            output.append("**Breakdown by Dimension**:\n")
            
            dimensions = breakdown.get('dimensions', {})
            
            # Create visual bar for each dimension
            for dim_name, dim_data in dimensions.items():
                reward = dim_data.get('reward', 0)
                
                # Get max possible reward based on dimension
                max_rewards = {
                    'test_passing': 50,
                    'partial_correctness': 15,
                    'code_quality': 10,
                    'efficiency': 10,
                    'improvement': 10,
                    'convergence': 5
                }
                max_reward = max_rewards.get(dim_name, 10)
                
                # Create progress bar
                percentage = (reward / max_reward) * 100 if max_reward > 0 else 0
                bar_length = int(percentage / 5)  # 20 chars = 100%
                bar = '█' * bar_length + '░' * (20 - bar_length)
                
                # Format dimension name
                display_name = dim_name.replace('_', ' ').title()
                
                output.append(f"- **{display_name}**: {bar} {reward:.1f}/{max_reward}")
                
                # Add details for specific dimensions
                if dim_name == 'test_passing':
                    output.append(f" ({passed}/{total} tests)")
                elif dim_name == 'partial_correctness' and 'average_similarity' in dim_data:
                    avg_sim = dim_data['average_similarity']
                    output.append(f" (avg similarity: {avg_sim:.2f})")
                elif dim_name == 'code_quality' and 'complexity_score' in dim_data:
                    complexity = dim_data['complexity_score']
                    output.append(f" (complexity: {complexity:.2f})")
                elif dim_name == 'efficiency' and 'execution_time' in dim_data:
                    time = dim_data['execution_time']
                    output.append(f" ({time:.2f}s)")
                
                output.append("\n")
            
            # Show penalties if any
            penalties = breakdown.get('penalties', 0)
            if penalties != 0:
                output.append(f"**Penalties**: {penalties:.2f}\n")
        else:
            # Fallback for old format
            basic_reward = iter_data.get('basic_reward', iter_data.get('reward', 0))
            output.append(f"**Reward**: {basic_reward:.2f} (basic scoring)\n")
        
        output.append(f"**Duration**: {iter_data['duration']:.2f}s\n")
        output.append("---\n")
    
    return '\n'.join(output)


def format_reward_comparison(metadata: Dict[str, Any]) -> str:
    """Create a comparison table showing reward evolution.
    
    Args:
        metadata: Refinement metadata
        
    Returns:
        Markdown table comparing iterations
    """
    if 'iterations' not in metadata or len(metadata['iterations']) == 0:
        return "No iteration data available."
    
    output = []
    output.append("# 📊 Reward Comparison Table\n")
    
    # Table header
    output.append("| Iter | Pass Rate | Test | Partial | Quality | Efficiency | Total |")
    output.append("|------|-----------|------|---------|---------|------------|-------|")
    
    for iter_data in metadata['iterations']:
        iteration = iter_data['iteration']
        pass_rate = iter_data['pass_rate']
        
        if 'reward_breakdown' in iter_data:
            breakdown = iter_data['reward_breakdown']
            dimensions = breakdown.get('dimensions', {})
            
            test_r = dimensions.get('test_passing', {}).get('reward', 0)
            partial_r = dimensions.get('partial_correctness', {}).get('reward', 0)
            quality_r = dimensions.get('code_quality', {}).get('reward', 0)
            efficiency_r = dimensions.get('efficiency', {}).get('reward', 0)
            total_r = breakdown.get('total_reward', 0)
            
            output.append(
                f"| {iteration} | {pass_rate:.1%} | "
                f"{test_r:.1f} | {partial_r:.1f} | {quality_r:.1f} | "
                f"{efficiency_r:.1f} | **{total_r:.1f}** |"
            )
        else:
            basic_reward = iter_data.get('basic_reward', iter_data.get('reward', 0))
            output.append(
                f"| {iteration} | {pass_rate:.1%} | "
                f"- | - | - | - | {basic_reward:.1f} |"
            )
    
    return '\n'.join(output)


def format_reward_json(metadata: Dict[str, Any]) -> str:
    """Format reward data as pretty-printed JSON.
    
    Args:
        metadata: Refinement metadata
        
    Returns:
        JSON string
    """
    # Extract just the reward-related data
    reward_data = {
        'converged': metadata.get('converged', False),
        'final_reward': metadata.get('final_reward', 0),
        'best_iteration': metadata.get('best_iteration', 0),
        'iterations': []
    }
    
    for iter_data in metadata.get('iterations', []):
        iter_summary = {
            'iteration': iter_data['iteration'],
            'pass_rate': round(iter_data['pass_rate'], 3),
            'duration': round(iter_data['duration'], 2)
        }
        
        if 'reward_breakdown' in iter_data:
            breakdown = iter_data['reward_breakdown']
            iter_summary['total_reward'] = breakdown.get('total_reward', 0)
            
            # Simplified dimension rewards
            iter_summary['rewards'] = {
                dim: round(data.get('reward', 0), 2)
                for dim, data in breakdown.get('dimensions', {}).items()
            }
            
            iter_summary['penalties'] = breakdown.get('penalties', 0)
        else:
            iter_summary['reward'] = iter_data.get('reward', 0)
        
        reward_data['iterations'].append(iter_summary)
    
    return json.dumps(reward_data, indent=2)


if __name__ == "__main__":
    # Test the visualization functions
    test_metadata = {
        'converged': False,
        'final_reward': 68.2,
        'best_iteration': 3,
        'iterations': [
            {
                'iteration': 1,
                'passed': 15,
                'failed': 7,
                'total': 22,
                'pass_rate': 0.682,
                'reward': 55.3,
                'duration': 1.2,
                'reward_breakdown': {
                    'total_reward': 55.3,
                    'penalties': -3.0,
                    'dimensions': {
                        'test_passing': {'reward': 34.1, 'pass_rate': 0.682},
                        'partial_correctness': {'reward': 8.5, 'average_similarity': 0.567},
                        'code_quality': {'reward': 6.2, 'complexity_score': 0.85},
                        'efficiency': {'reward': 7.5, 'execution_time': 0.8},
                        'improvement': {'reward': 0, 'prev_pass_rate': None},
                        'convergence': {'reward': 0}
                    }
                }
            },
            {
                'iteration': 2,
                'passed': 18,
                'failed': 4,
                'total': 22,
                'pass_rate': 0.818,
                'reward': 65.8,
                'duration': 0.9,
                'reward_breakdown': {
                    'total_reward': 65.8,
                    'penalties': 0,
                    'dimensions': {
                        'test_passing': {'reward': 40.9, 'pass_rate': 0.818},
                        'partial_correctness': {'reward': 11.2, 'average_similarity': 0.745},
                        'code_quality': {'reward': 5.8, 'complexity_score': 0.80},
                        'efficiency': {'reward': 6.5, 'execution_time': 1.1},
                        'improvement': {'reward': 1.36, 'prev_pass_rate': 0.682},
                        'convergence': {'reward': 0}
                    }
                }
            },
            {
                'iteration': 3,
                'passed': 18,
                'failed': 4,
                'total': 22,
                'pass_rate': 0.818,
                'reward': 68.2,
                'duration': 0.5,
                'reward_breakdown': {
                    'total_reward': 68.2,
                    'penalties': 0,
                    'dimensions': {
                        'test_passing': {'reward': 40.9, 'pass_rate': 0.818},
                        'partial_correctness': {'reward': 14.3, 'average_similarity': 0.95},
                        'code_quality': {'reward': 4.3, 'complexity_score': 0.70},
                        'efficiency': {'reward': 8.0, 'execution_time': 0.5},
                        'improvement': {'reward': 0.7, 'prev_pass_rate': 0.818},
                        'convergence': {'reward': 0}
                    }
                }
            }
        ]
    }
    
    print("=" * 80)
    print("TESTING VISUALIZATION FUNCTIONS")
    print("=" * 80)
    
    print("\n1. DETAILED BREAKDOWN:\n")
    print(format_reward_breakdown(test_metadata))
    
    print("\n2. COMPARISON TABLE:\n")
    print(format_reward_comparison(test_metadata))
    
    print("\n3. JSON OUTPUT:\n")
    print(format_reward_json(test_metadata))
