"""CLI Orchestration Layer - Main entry point for Auto-TDD system."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import json
import traceback

from config import Config
from logger import logger
from utils import generate_run_id, calculate_code_hash
from parser import PromptParser
from test_generator import TestGenerator
from code_generator import CodeGenerator
from sandbox_runner import SandboxRunner
from failure_analyzer import FailureAnalyzer
from refine_loop import RefinementLoop
from quality_checks import QualityChecker
from metrics import MetricsCollector

class AutoTDD:
    """Main orchestrator for Auto-TDD system."""
    
    def __init__(self, args):
        self.args = args
        self.run_id = generate_run_id()
        self.output_dir = None
        
        # Initialize modules
        self.parser = PromptParser()
        self.test_generator = TestGenerator()
        self.code_generator = CodeGenerator()
        self.quality_checker = QualityChecker()
        self.refinement_loop = RefinementLoop()
        
        Config.ensure_directories()
    
    def run(self) -> int:
        """Execute the complete Auto-TDD pipeline.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            logger.info("=" * 60)
            logger.info("Auto-TDD System Starting", run_id=self.run_id)
            logger.info("=" * 60)
            
            # Phase 1: Parse prompt
            logger.info("\n[Phase 1/6] Parsing problem specification...")
            spec = self._parse_prompt()
            logger.info(f"✓ Parsed: {spec.function_name}", 
                       params=len(spec.parameters))
            
            # Phase 2: Generate tests
            logger.info("\n[Phase 2/6] Generating test suite...")
            test_code = self._generate_tests(spec)
            logger.info(f"✓ Generated {self.test_generator.test_count} tests")
            
            # Phase 3: Generate initial code
            logger.info("\n[Phase 3/6] Generating initial implementation...")
            initial_code, gen_metadata = self._generate_code(spec, test_code)
            logger.info("✓ Initial code generated", 
                       method=gen_metadata.get('method'))
            
            # Phase 4: Quality check
            logger.info("\n[Phase 4/6] Running quality checks...")
            quality_result = self.quality_checker.check(initial_code)
            if quality_result['syntax_error']:
                logger.warning("⚠ Syntax errors detected, will attempt to fix")
            logger.info("✓ Quality check completed",
                       complexity=quality_result['complexity'],
                       security_issues=quality_result['security_issues'])
            
            # Phase 5: Refinement loop
            logger.info("\n[Phase 5/6] Starting iterative refinement...")
            final_code, refine_metadata = self._refine_code(
                spec, 
                initial_code, 
                test_code
            )
            
            # Phase 6: Final validation
            logger.info("\n[Phase 6/6] Final validation...")
            success = self._final_validation(
                spec,
                final_code,
                test_code,
                refine_metadata
            )
            
            # Save artifacts
            self._save_artifacts(spec, final_code, test_code, refine_metadata)
            
            # Print summary
            self._print_summary(spec, success, refine_metadata)
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            logger.warning("\n\nInterrupted by user")
            return 130
        except Exception as e:
            logger.error("Fatal error", error=str(e))
            logger.error(traceback.format_exc())
            return 1
        finally:
            self._cleanup()
    
    def _parse_prompt(self):
        """Parse natural language prompt."""
        prompt = self.args.prompt
        
        # Load from file if provided
        if self.args.prompt_file:
            prompt_path = Path(self.args.prompt_file)
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            prompt = prompt_path.read_text()
        
        if not prompt:
            raise ValueError("No prompt provided")
        
        spec = self.parser.parse(prompt)
        return spec
    
    def _generate_tests(self, spec):
        """Generate test suite."""
        test_code = self.test_generator.generate(spec)
        return test_code
    
    def _generate_code(self, spec, test_code):
        """Generate initial implementation."""
        code, metadata = self.code_generator.generate(spec, test_code)
        return code, metadata
    
    def _refine_code(self, spec, code, test_code):
        """Run refinement loop."""
        final_code, metadata = self.refinement_loop.refine(
            spec,
            code,
            test_code
        )
        return final_code, metadata
    
    def _final_validation(self, spec, code, test_code, refine_metadata):
        """Perform final validation."""
        sandbox = SandboxRunner()
        
        try:
            result = sandbox.run_tests(code, test_code)
            
            success = (
                result.failed == 0 and 
                result.errors == 0 and 
                result.passed > 0
            )
            
            if success:
                logger.info("✓ All tests passed!",
                           passed=result.passed,
                           total=result.total)
            else:
                logger.warning("✗ Some tests failed",
                              passed=result.passed,
                              failed=result.failed,
                              errors=result.errors)
            
            return success
            
        finally:
            sandbox.cleanup()
    
    def _save_artifacts(self, spec, code, test_code, refine_metadata):
        """Save all artifacts to output directory."""
        # Create output directory
        self.output_dir = Config.ARTIFACTS_DIR / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Saving artifacts", output_dir=str(self.output_dir))
        
        # Save specification
        spec_file = self.output_dir / "spec.json"
        spec_file.write_text(spec.to_json())
        
        # Save implementation
        impl_file = self.output_dir / "impl.py"
        impl_file.write_text(code)
        
        # Save tests
        test_file = self.output_dir / "test_impl.py"
        test_file.write_text(test_code)
        
        # Save refinement metadata
        metadata_file = self.output_dir / "refinement.json"
        metadata_file.write_text(json.dumps(refine_metadata, indent=2))
        
        # Save quality report
        quality_result = self.quality_checker.check(code)
        quality_file = self.output_dir / "quality.json"
        quality_file.write_text(json.dumps(quality_result, indent=2))
        
        logger.info("✓ Artifacts saved", location=str(self.output_dir))
    
    def _print_summary(self, spec, success, refine_metadata):
        """Print execution summary."""
        print("\n" + "=" * 60)
        print("AUTO-TDD EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Run ID: {self.run_id}")
        print(f"Function: {spec.function_name}")
        print(f"Status: {'✓ SUCCESS' if success else '✗ FAILED'}")
        print(f"\nIterations: {len(refine_metadata.get('iterations', []))}")
        print(f"Converged: {refine_metadata.get('converged', False)}")
        
        if refine_metadata.get('iterations'):
            final_iter = refine_metadata['iterations'][-1]
            print(f"\nFinal Results:")
            print(f"  Tests Passed: {final_iter['passed']}/{final_iter['total']}")
            print(f"  Pass Rate: {final_iter['pass_rate']*100:.1f}%")
            print(f"  Reward: {final_iter.get('reward', 0):.2f}")
        
        print(f"\nArtifacts: {self.output_dir}")
        print("=" * 60)
    
    def _cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'refinement_loop'):
                self.refinement_loop.cleanup()
        except Exception as e:
            logger.warning("Cleanup failed", error=str(e))

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-TDD: Automated Test-Driven Development System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with inline prompt
  python cli.py --prompt "Write a function to calculate factorial"
  
  # Using prompt from file
  python cli.py --prompt-file problem.txt --timeout 300
  
  # Custom configuration
  python cli.py --prompt "Sort a list" --max-iterations 10
        """
    )
    
    parser.add_argument(
        '--prompt',
        type=str,
        help='Problem description in natural language'
    )
    
    parser.add_argument(
        '--prompt-file',
        type=str,
        help='Path to file containing problem description'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Total execution timeout in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=Config.MAX_ITERATIONS,
        help=f'Maximum refinement iterations (default: {Config.MAX_ITERATIONS})'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Custom output directory for artifacts'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Auto-TDD v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.prompt and not args.prompt_file:
        parser.error("Either --prompt or --prompt-file must be provided")
    
    # Update config from args
    if args.max_iterations:
        Config.MAX_ITERATIONS = args.max_iterations
    
    if args.output_dir:
        Config.ARTIFACTS_DIR = Path(args.output_dir)
    
    if args.verbose:
        Config.LOG_LEVEL = "DEBUG"
    
    # Run Auto-TDD
    auto_tdd = AutoTDD(args)
    exit_code = auto_tdd.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
