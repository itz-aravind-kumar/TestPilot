"""Quick script to fix all yield statements in gradio_app.py"""
import re

with open('gradio_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to match old yield format
old_pattern = r'yield \(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^\)]+)\s*\)'

def replacement(match):
    logs, phase, progress, tests, init, final, iters, thoughts = match.groups()
    return f'''yield yield_update(
            logs={logs.strip()},
            phase={phase.strip()},
            prog={progress.strip()},
            tests={tests.strip()},
            init_code={init.strip()},
            final={final.strip()},
            iters={iters.strip()},
            thoughts={thoughts.strip()}
        )'''

# Replace all occurrences
new_content = re.sub(old_pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

# Count changes
old_count = len(re.findall(old_pattern, content))
print(f"Replaced {old_count} yield statements")

with open('gradio_app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ Done!")
