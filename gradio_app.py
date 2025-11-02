"""
Auto-TDD Gradio Frontend
A comprehensive UI for the Auto-TDD system with real-time monitoring and chain-of-thought reasoning
"""
import gradio as gr
import sys
from pathlib import Path
import threading
import time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from parser import PromptParser
from test_generator import TestGenerator
from code_generator import CodeGenerator
from refine_loop import RefinementLoop
from sandbox_runner import SandboxRunner
from quality_checks import QualityChecker
from logger import logger
import logging

# Custom handler to capture logs into UI state
class UILogHandler(logging.Handler):
    def __init__(self, state):
        super().__init__()
        self.state = state
    
    def emit(self, record):
        log_message = self.format(record)
        # Extract just the message part (after the timestamp/level)
        if " - " in log_message:
            parts = log_message.split(" - ", 3)
            if len(parts) >= 4:
                message = parts[3]
            else:
                message = log_message
        else:
            message = log_message
        
        # Add to appropriate log buffer
        if "[SANDBOX]" in message or "SANDBOX:" in message:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.state.sandbox_logs.append(f"[{timestamp}] {message}")

# Global state for real-time updates
class AutoTDDState:
    def __init__(self):
        self.logs = []
        self.sandbox_logs = []  # Separate logs for sandbox events
        self.current_phase = "Idle"
        self.progress = 0
        self.spec = None
        self.test_code = ""
        self.current_code = ""
        self.final_code = ""
        self.iterations = []
        self.chain_of_thought = []
        self.is_running = False
        
    def add_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        
        # Also capture sandbox-specific logs (updated to match new format)
        if "[SANDBOX]" in message or "SANDBOX:" in message:
            self.sandbox_logs.append(log_entry)
        
        return "\n".join(self.logs[-100:])  # Keep last 100 logs
    
    def get_sandbox_logs(self):
        """Get only sandbox-related logs"""
        if not self.sandbox_logs:
            return "[Waiting for sandbox activity...]\n\nSandbox logs will appear here when tests run."
        return "\n".join(self.sandbox_logs[-50:])
    
    def add_thought(self, thought):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chain_of_thought.append(f"[{timestamp}] {thought}")
        return "\n".join(self.chain_of_thought)

state = AutoTDDState()

# Attach UI log handler to capture sandbox logs
ui_handler = UILogHandler(state)
ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger('auto_tdd').addHandler(ui_handler)

def yield_update(logs=None, phase=None, prog=None, tests="", init_code="", final="", iters="", thoughts=None):
    """Helper to yield updates with consistent structure"""
    return (
        logs if logs else state.add_log(""),
        state.get_sandbox_logs(),  # Always include sandbox logs
        phase if phase else state.current_phase,
        prog if prog is not None else state.progress,
        tests,
        init_code,
        final,
        iters,
        thoughts if thoughts else state.add_thought("")
    )

def format_code_block(code, language="python"):
    """Format code with syntax highlighting"""
    if not code:
        return "No code generated yet."
    return f"```{language}\n{code}\n```"

def run_auto_tdd(problem_description):
    """Main Auto-TDD execution pipeline"""
    state.is_running = True
    state.logs = []
    state.chain_of_thought = []
    state.iterations = []
    state.progress = 0
    
    try:
        # Initialize components
        state.add_log("Initializing Auto-TDD system...")
        parser = PromptParser()
        test_gen = TestGenerator()
        code_gen = CodeGenerator()
        sandbox = SandboxRunner()
        quality = QualityChecker()
        refiner = RefinementLoop()
        
        # Phase 1: Parse Problem
        state.current_phase = "Phase 1/6: Parsing Problem"
        state.progress = 10
        state.add_log("=" * 60)
        state.add_log("PHASE 1: PARSING PROBLEM SPECIFICATION")
        state.add_log("=" * 60)
        state.add_thought("Starting problem analysis...")
        state.add_thought("Reading problem description and extracting key information...")
        
        yield yield_update(
            logs=state.add_log("Parsing problem description..."),
            phase=state.current_phase,
            prog=state.progress,
            thoughts=state.add_thought("Identifying function name, parameters, and requirements...")
        )
        
        state.spec = parser.parse(problem_description)
        
        state.add_log(f"✓ Function identified: {state.spec.function_name}")
        state.add_log(f"✓ Parameters: {[p.name for p in state.spec.parameters]}")
        state.add_log(f"✓ Return type: {state.spec.return_type}")
        state.add_thought(f"Problem understood: Implementing '{state.spec.function_name}' function")
        state.add_thought(f"Function takes {len(state.spec.parameters)} parameter(s)")
        
        # Phase 2: Generate Tests
        state.current_phase = "Phase 2/6: Generating Tests"
        state.progress = 25
        state.add_log("\n" + "=" * 60)
        state.add_log("PHASE 2: LLM GENERATING TEST CASES")
        state.add_log("=" * 60)
        state.add_thought("Calling LLM to generate comprehensive test suite...")
        state.add_thought("Tests will cover: happy path, edge cases, and error handling")
        
        yield yield_update(
            logs=state.add_log("⚡ LLM generating test cases..."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(""),
            init_code="",
            final="",
            iters="",
            thoughts=state.add_thought("LLM is analyzing the problem and creating test scenarios..."
        )
        )
        
        state.test_code = test_gen.generate(state.spec)
        
        state.add_log(f"✓ Generated {test_gen.test_count} tests")
        state.add_log(f"✓ Test code: {len(state.test_code)} characters")
        state.add_thought(f"Test generation complete: {test_gen.test_count} tests created")
        state.add_thought("Tests include: basic functionality, edge cases, and type validation")
        
        # Phase 3: Generate Initial Code
        state.current_phase = "Phase 3/6: Generating Code"
        state.progress = 40
        state.add_log("\n" + "=" * 60)
        state.add_log("PHASE 3: LLM GENERATING INITIAL IMPLEMENTATION")
        state.add_log("=" * 60)
        state.add_thought("Calling LLM to generate initial code implementation...")
        state.add_thought("LLM will analyze tests and create a working implementation")
        
        yield yield_update(
            logs=state.add_log("⚡ LLM generating code implementation..."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code="",
            final="",
            iters="",
            thoughts=state.add_thought("LLM is synthesizing code from test requirements..."
        )
        )
        
        state.current_code, gen_metadata = code_gen.generate(state.spec, state.test_code)
        
        state.add_log(f"✓ Code generated using: {gen_metadata.get('method', 'unknown')}")
        state.add_log(f"✓ Model: {gen_metadata.get('model', 'N/A')}")
        state.add_log(f"✓ Code length: {len(state.current_code)} characters")
        state.add_thought(f"Initial code generated using {gen_metadata.get('method', 'unknown')} method")
        
        # Phase 4: Quality Check
        state.current_phase = "Phase 4/6: Quality Analysis"
        state.progress = 55
        state.add_log("\n" + "=" * 60)
        state.add_log("PHASE 4: QUALITY CHECKS")
        state.add_log("=" * 60)
        state.add_thought("Running quality analysis on generated code...")
        
        yield yield_update(
            logs=state.add_log("Analyzing code quality..."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code=format_code_block(state.current_code),
            final="",
            iters="",
            thoughts=state.add_thought("Checking: syntax, complexity, security issues..."
        )
        )
        
        quality_result = quality.check(state.current_code)
        
        state.add_log(f"✓ Complexity: {quality_result.get('complexity', 'N/A')}")
        state.add_log(f"✓ Security issues: {quality_result.get('security_issues', 0)}")
        if quality_result.get('syntax_error'):
            state.add_log(f"⚠ Syntax error: {quality_result.get('syntax_error')}", "WARNING")
            state.add_thought("Syntax error detected - will attempt to fix during refinement")
        else:
            state.add_log("✓ No syntax errors")
            state.add_thought("Code passes initial quality checks")
        
        # Phase 5: Refinement Loop
        state.current_phase = "Phase 5/6: RL Refinement Loop"
        state.progress = 70
        state.add_log("\n" + "=" * 60)
        state.add_log("PHASE 5: RL-BASED REFINEMENT LOOP")
        state.add_log("=" * 60)
        state.add_thought("Starting iterative refinement with reinforcement learning...")
        state.add_thought("Each iteration: Test → Analyze → Reward → Improve → Repeat")
        
        yield yield_update(
            logs=state.add_log("🔄 Starting refinement loop..."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code=format_code_block(state.current_code),
            final="",
            iters=format_iteration_table([]),
            thoughts=state.add_thought("Will iterate until tests pass or max iterations reached..."
        )
        )
        
        state.final_code, refine_metadata = refiner.refine(
            state.spec,
            state.current_code,
            state.test_code
        )
        
        # Store iterations with full reward breakdown
        if refine_metadata.get('iterations'):
            for iteration in refine_metadata['iterations']:
                state.iterations.append({
                    'iteration': iteration.get('iteration', 0),
                    'passed': iteration.get('passed', 0),
                    'failed': iteration.get('failed', 0),
                    'reward': iteration.get('reward', 0),
                    'pass_rate': iteration.get('pass_rate', 0),
                    'reward_breakdown': iteration.get('reward_breakdown', {})  # NEW: Store full breakdown
                })
                iter_num = iteration.get('iteration', 0)
                state.add_thought(f"Iteration {iter_num}: {iteration.get('passed', 0)} passed, {iteration.get('failed', 0)} failed, reward: {iteration.get('reward', 0):.2f}")
        
        best_iter = refine_metadata.get('best_iteration', 0)
        state.add_log(f"✓ Refinement complete: {len(refine_metadata.get('iterations', []))} iterations")
        state.add_log(f"✓ Best solution from iteration {best_iter} with reward: {refine_metadata.get('final_reward', 'N/A')}")
        if best_iter > 0:
            state.add_thought(f"Using code from iteration {best_iter} as it had the highest reward")
        
        # Phase 6: Final Validation
        state.current_phase = "Phase 6/6: Final Validation"
        state.progress = 90
        state.add_log("\n" + "=" * 60)
        state.add_log("PHASE 6: FINAL VALIDATION")
        state.add_log("=" * 60)
        state.add_thought("Running final validation test in Docker sandbox...")
        
        yield yield_update(
            logs=state.add_log("🐳 Testing in Docker sandbox..."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code=format_code_block(state.current_code),
            final=format_code_block(state.final_code),
            iters=format_iteration_table(state.iterations),
            thoughts=state.add_thought("Executing all tests in isolated environment..."
        )
        )
        
        final_result = sandbox.run_tests(state.final_code, state.test_code)
        
        success = (final_result.exit_code == 0 and final_result.failed == 0)
        
        state.progress = 100
        state.current_phase = "✅ Complete" if success else "⚠ Incomplete"
        
        if success:
            state.add_log("\n" + "=" * 60)
            state.add_log("✅ SUCCESS! ALL TESTS PASSED!", "SUCCESS")
            state.add_log("=" * 60)
            state.add_log(f"✓ Tests Passed: {final_result.passed}")
            state.add_log(f"✓ Duration: {final_result.duration:.2f}s")
            state.add_thought("🎉 SUCCESS! Generated code passes all tests!")
            state.add_thought(f"Final code is production-ready with {final_result.passed} passing tests")
        else:
            state.add_log("\n" + "=" * 60)
            state.add_log("⚠ INCOMPLETE - Code has issues", "WARNING")
            state.add_log("=" * 60)
            state.add_log(f"Tests Passed: {final_result.passed}")
            state.add_log(f"Tests Failed: {final_result.failed}")
            state.add_thought("Code still has issues after refinement")
            state.add_thought("May need more iterations or different approach")
        
        state.is_running = False
        
        yield yield_update(
            logs=state.add_log("Process complete."),
            phase=state.current_phase,
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code=format_code_block(state.current_code),
            final=format_code_block(state.final_code),
            iters=format_iteration_table(state.iterations),
            thoughts=state.add_thought("Auto-TDD process finished."
        )
        )
        
    except Exception as e:
        state.is_running = False
        state.add_log(f"❌ ERROR: {str(e)}", "ERROR")
        state.add_thought(f"Error occurred: {type(e).__name__}: {str(e)}")
        import traceback
        state.add_log(traceback.format_exc(), "ERROR")
        
        yield yield_update(
            logs=state.add_log("Process failed with error."),
            phase="❌ Error",
            prog=state.progress,
            tests=format_code_block(state.test_code),
            init_code=format_code_block(state.current_code),
            final=format_code_block(state.final_code),
            iters=format_iteration_table(state.iterations),
            thoughts=state.add_thought("Process terminated due to error."
        )
        )

def format_iteration_table(iterations):
    """Format iteration history with detailed reward breakdown"""
    if not iterations:
        return "No iterations yet."
    
    # Enhanced reward breakdown display
    output = "# 🎯 Iteration Results with Reward Breakdown\n\n"
    
    # Summary table with all dimensions
    output += "## Quick Summary\n\n"
    output += "| Iter | Tests | Pass Rate | Test | Partial | Quality | Efficiency | Improve | Conv | **Total** |\n"
    output += "|------|-------|-----------|------|---------|---------|------------|---------|------|----------|\n"
    
    for it in iterations:
        passed = it['passed']
        failed = it['failed']
        total_tests = passed + failed
        pass_rate = it['pass_rate']
        total_reward = it['reward']
        
        # Extract reward breakdown if available
        breakdown = it.get('reward_breakdown', {})
        dimensions = breakdown.get('dimensions', {})
        
        if dimensions:
            # Enhanced RL rewards (new system)
            test_r = dimensions.get('test_passing', {}).get('reward', 0)
            partial_r = dimensions.get('partial_correctness', {}).get('reward', 0)
            quality_r = dimensions.get('code_quality', {}).get('reward', 0)
            efficiency_r = dimensions.get('efficiency', {}).get('reward', 0)
            improve_r = dimensions.get('improvement', {}).get('reward', 0)
            conv_r = dimensions.get('convergence', {}).get('reward', 0)
            
            output += f"| {it['iteration']} | {passed}/{total_tests} | {pass_rate:.1%} | "
            output += f"{test_r:.1f} | {partial_r:.1f} | {quality_r:.1f} | {efficiency_r:.1f} | "
            output += f"{improve_r:.1f} | {conv_r:.1f} | **{total_reward:.1f}** |\n"
        else:
            # Basic reward (old system)
            output += f"| {it['iteration']} | {passed}/{total_tests} | {pass_rate:.1%} | "
            output += f"- | - | - | - | - | - | **{total_reward:.1f}** |\n"
    
    # Detailed breakdown for each iteration
    output += "\n## Detailed Breakdown\n\n"
    
    for it in iterations:
        iter_num = it['iteration']
        passed = it['passed']
        failed = it['failed']
        total_tests = passed + failed
        pass_rate = it['pass_rate']
        total_reward = it['reward']
        
        output += f"### Iteration {iter_num}\n\n"
        output += f"**Tests**: {passed}/{total_tests} passed ({pass_rate:.1%})\n\n"
        
        breakdown = it.get('reward_breakdown', {})
        
        if breakdown and breakdown.get('dimensions'):
            dimensions = breakdown.get('dimensions', {})
            penalties = breakdown.get('penalties', 0)
            
            output += f"**Total Reward**: {total_reward:.2f}/100.0\n\n"
            output += "**Reward Contributions**:\n\n"
            
            # Progress bars for each dimension
            dimension_info = {
                'test_passing': ('Test Passing', 50, '🎯'),
                'partial_correctness': ('Partial Correctness', 15, '📊'),
                'code_quality': ('Code Quality', 10, '✨'),
                'efficiency': ('Efficiency', 10, '⚡'),
                'improvement': ('Improvement', 10, '📈'),
                'convergence': ('Convergence', 5, '🏆')
            }
            
            for dim_key, (dim_name, max_reward, emoji) in dimension_info.items():
                if dim_key in dimensions:
                    dim_data = dimensions[dim_key]
                    reward = dim_data.get('reward', 0)
                    
                    # Create progress bar
                    percentage = (reward / max_reward * 100) if max_reward > 0 else 0
                    bar_length = int(percentage / 5)  # 20 chars = 100%
                    bar = '█' * bar_length + '░' * (20 - bar_length)
                    
                    output += f"{emoji} **{dim_name}**: {bar} {reward:.1f}/{max_reward}\n"
                    
                    # Add dimension-specific details
                    if dim_key == 'test_passing':
                        output += f"   ↳ {passed}/{total_tests} tests passed\n"
                    elif dim_key == 'partial_correctness' and 'average_similarity' in dim_data:
                        avg_sim = dim_data['average_similarity']
                        count = dim_data.get('similarity_count', 0)
                        if count > 0:
                            output += f"   ↳ Avg similarity: {avg_sim:.2f} across {count} failures\n"
                    elif dim_key == 'code_quality':
                        if 'complexity_score' in dim_data:
                            complexity = dim_data['complexity_score']
                            output += f"   ↳ Complexity score: {complexity:.2f}\n"
                        if 'pythonic_patterns' in dim_data:
                            patterns = dim_data['pythonic_patterns']
                            if patterns:
                                output += f"   ↳ Patterns: {', '.join(patterns[:3])}\n"
                    elif dim_key == 'efficiency':
                        if 'execution_time' in dim_data:
                            exec_time = dim_data['execution_time']
                            output += f"   ↳ Execution: {exec_time:.2f}s\n"
                        if 'estimated_complexity' in dim_data:
                            complexity = dim_data['estimated_complexity']
                            output += f"   ↳ Estimated: {complexity}\n"
                    elif dim_key == 'improvement' and 'improvement' in dim_data:
                        improvement = dim_data['improvement']
                        if improvement != 0:
                            output += f"   ↳ Pass rate change: {improvement:+.1%}\n"
                    
                    output += "\n"
            
            if penalties != 0:
                output += f"⚠️ **Penalties**: {penalties:.2f}\n\n"
        else:
            # Old system without breakdown
            output += f"**Reward**: {total_reward:.2f} (basic scoring)\n\n"
        
        output += "---\n\n"
    
    return output

def build_problem_from_structured(func_name, func_desc, params, return_type, examples, constraints):
    """Build natural language problem from structured inputs"""
    if not func_name or not func_desc:
        return None
    
    problem = f"Write a Python function called {func_name} that {func_desc}\n\n"
    
    if params:
        problem += "Parameters:\n"
        for param in params.strip().split('\n'):
            if param.strip():
                problem += f"- {param.strip()}\n"
        problem += "\n"
    
    if return_type:
        problem += f"Return Type: {return_type}\n\n"
    
    if examples:
        problem += "Examples:\n"
        for example in examples.strip().split('\n'):
            if example.strip():
                problem += f"- {example.strip()}\n"
        problem += "\n"
    
    if constraints:
        problem += "Requirements:\n"
        for constraint in constraints.strip().split('\n'):
            if constraint.strip():
                problem += f"- {constraint.strip()}\n"
    
    return problem

def run_auto_tdd_wrapper(input_mode, natural_problem, func_name, func_desc, params, return_type, examples, constraints):
    """Wrapper to handle both input modes"""
    if input_mode == "Natural Language":
        problem = natural_problem
    else:
        problem = build_problem_from_structured(func_name, func_desc, params, return_type, examples, constraints)
        if not problem:
            yield yield_update(
            logs="[ERROR] Please fill in at least Function Name and Description",
            phase="❌ Error",
            prog=0,
            tests="",
            init_code="",
            final="",
            iters="",
            thoughts=""
        )
            return
    
    # Run the actual Auto-TDD pipeline
    yield from run_auto_tdd(problem)

# Create Gradio Interface
with gr.Blocks(title="Auto TDD — Make tests do the heavy lifting", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🤖 Auto TDD — Make tests do the heavy lifting
    
    **Generate working code from natural language using AI + RL + Docker**
    
    This system:
    1. Parses your problem description
    2. LLM generates comprehensive test cases
    3. LLM generates initial code implementation
    4. Tests code in isolated Docker sandbox
    5. Analyzes failures with chain-of-thought reasoning
    6. Refines code using reinforcement learning
    7. Iterates until all tests pass
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 📝 Input Method")
            
            input_mode = gr.Radio(
                choices=["Natural Language", "Structured Form"],
                value="Natural Language",
                label="Input Mode",
                info="Choose how you want to describe your problem"
            )
            
            # Natural Language Input
            with gr.Group(visible=True) as natural_input:
                problem_input = gr.Textbox(
                    label="Problem Description",
                    placeholder="Write a function called calculate_factorial that takes a positive integer n and returns its factorial...",
                    lines=15,
                    value="""Write a Python function called calculate_factorial that takes a positive integer n and returns its factorial.

Factorial of n (written as n!) is the product of all positive integers less than or equal to n.
For example: 5! = 5 x 4 x 3 x 2 x 1 = 120

Examples:
- calculate_factorial(0) returns 1
- calculate_factorial(1) returns 1
- calculate_factorial(5) returns 120
- calculate_factorial(10) returns 3628800

Requirements:
- Handle n = 0 (returns 1)
- Handle n = 1 (returns 1)
- Calculate correctly for any positive integer"""
                )
            
            # Structured Form Input
            with gr.Group(visible=False) as structured_input:
                func_name = gr.Textbox(
                    label="Function Name",
                    placeholder="e.g., calculate_factorial",
                    value=""
                )
                func_description = gr.Textbox(
                    label="Function Description",
                    placeholder="Brief description of what the function does",
                    lines=3,
                    value=""
                )
                func_params = gr.Textbox(
                    label="Parameters (one per line)",
                    placeholder="n: int - The input number\nbase: int = 10 - Optional base",
                    lines=3,
                    value=""
                )
                func_return = gr.Textbox(
                    label="Return Type",
                    placeholder="e.g., int, str, List[int]",
                    value=""
                )
                func_examples = gr.Textbox(
                    label="Examples (one per line)",
                    placeholder="calculate_factorial(5) = 120\ncalculate_factorial(0) = 1",
                    lines=4,
                    value=""
                )
                func_constraints = gr.Textbox(
                    label="Constraints/Requirements (one per line)",
                    placeholder="Input must be non-negative\nMust handle n = 0",
                    lines=3,
                    value=""
                )
            
            run_btn = gr.Button("🚀 Run Auto-TDD", variant="primary", size="lg")
            
            # Function to toggle input visibility
            def toggle_input_mode(mode):
                if mode == "Natural Language":
                    return gr.update(visible=True), gr.update(visible=False)
                else:
                    return gr.update(visible=False), gr.update(visible=True)
            
            input_mode.change(
                fn=toggle_input_mode,
                inputs=[input_mode],
                outputs=[natural_input, structured_input]
            )
            
            with gr.Row():
                current_phase = gr.Textbox(label="Current Phase", value="Idle", interactive=False)
                progress = gr.Number(label="Progress (%)", value=0, interactive=False)
    
    with gr.Tabs():
        with gr.Tab("📊 Logs & Monitoring"):
            logs_output = gr.Textbox(
                label="System Logs",
                lines=20,
                interactive=False,
                show_label=True
            )
        
        with gr.Tab("🐳 Docker Sandbox"):
            gr.Markdown("""
            ### 🔒 Isolated Test Execution Environment
            
            **Every test run happens in a secure Docker sandbox:**
            - **Image**: `auto-tdd-pytest:latest` (pure Python 3.10 + pytest)
            - **Memory Limit**: 50MB (prevents resource abuse)
            - **CPU Quota**: 50% (fair resource allocation)
            - **Network**: DISABLED (no external access)
            - **Filesystem**: READ-ONLY (immutable code)
            - **Timeout**: 10 seconds (prevents hanging)
            - **Lifecycle**: Container destroyed after execution
            
            **Watch the logs below to see containers spin up in real-time!**
            """)
            sandbox_logs = gr.Textbox(
                label="Sandbox Container Events (Live)",
                lines=15,
                interactive=False,
                show_label=True,
                placeholder="[Sandbox events will appear here when tests run...]"
            )
        
        with gr.Tab("🧠 Chain of Thought"):
            thought_output = gr.Textbox(
                label="Reasoning Process",
                lines=20,
                interactive=False,
                show_label=True,
                placeholder="Chain-of-thought reasoning will appear here..."
            )
        
        with gr.Tab("🧪 Generated Tests"):
            test_output = gr.Markdown(
                label="Test Code",
                value="No tests generated yet."
            )
        
        with gr.Tab("💻 Initial Code"):
            initial_code_output = gr.Markdown(
                label="Initial Implementation",
                value="No code generated yet."
            )
        
        with gr.Tab("✅ Final Code"):
            final_code_output = gr.Markdown(
                label="Final Refined Code",
                value="No final code yet."
            )
        
        with gr.Tab("📈 Iterations"):
            iterations_output = gr.Markdown(
                label="Refinement History",
                value="No iterations yet."
            )
    
    # Connect the run button
    run_btn.click(
        fn=run_auto_tdd_wrapper,
        inputs=[
            input_mode,
            problem_input,
            func_name,
            func_description,
            func_params,
            func_return,
            func_examples,
            func_constraints
        ],
        outputs=[
            logs_output,
            sandbox_logs,
            current_phase,
            progress,
            test_output,
            initial_code_output,
            final_code_output,
            iterations_output,
            thought_output
        ]
    )
    
    gr.Markdown("""
    ---
    ### 📖 How It Works:
    
    1. **Parse**: Extracts function requirements from natural language
    2. **Generate Tests**: LLM creates comprehensive test suite
    3. **Generate Code**: LLM implements initial solution
    4. **Quality Check**: Validates syntax, complexity, security
    5. **RL Refinement**: Iteratively improves code based on test results
    6. **Validate**: Final Docker sandbox testing
    
    ### 🎯 Features:
    - ✅ Real-time logs and monitoring
    - ✅ Chain-of-thought reasoning display
    - ✅ Iteration history with rewards
    - ✅ Docker sandbox isolation
    - ✅ Reinforcement learning optimization
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
