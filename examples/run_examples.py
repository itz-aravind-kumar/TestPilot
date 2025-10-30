"""Example usage of Auto-TDD system."""
import subprocess
import sys
from pathlib import Path

def run_example(prompt: str, description: str):
    """Run Auto-TDD with an example prompt."""
    print("\n" + "=" * 70)
    print(f"EXAMPLE: {description}")
    print("=" * 70)
    print(f"Prompt: {prompt}")
    print("-" * 70)
    
    result = subprocess.run(
        [sys.executable, "cli.py", "--prompt", prompt],
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0

def main():
    """Run multiple examples."""
    examples = [
        (
            "Write a function that reverses a string",
            "Simple String Reversal"
        ),
        (
            "Create a function that checks if a number is prime",
            "Prime Number Checker"
        ),
        (
            "Implement a function to find the GCD of two numbers",
            "Greatest Common Divisor"
        ),
        (
            "Write a function that removes duplicates from a list while preserving order",
            "Remove Duplicates"
        ),
    ]
    
    print("\nAuto-TDD Example Runner")
    print("=" * 70)
    print(f"Running {len(examples)} examples...\n")
    
    success_count = 0
    
    for prompt, description in examples:
        success = run_example(prompt, description)
        if success:
            success_count += 1
        
        print("\n" + "=" * 70)
        input("Press Enter to continue to next example...")
    
    print(f"\n\nCompleted: {success_count}/{len(examples)} examples successful")

if __name__ == "__main__":
    main()
