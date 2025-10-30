"""Remove all Unicode emojis/symbols from Python files for Windows compatibility"""
import re

files_to_fix = ['cli.py', 'refine_loop.py', 'gradio_app.py', 'sandbox_runner.py']

replacements = {
    '✓': '[OK]',
    '✅': '[OK]',
    '❌': '[FAIL]',
    '🎯': '[TARGET]',
    '🚀': '[LAUNCH]',
    '⚡': '[FAST]',
    '💡': '[TIP]',
    '🔍': '[SEARCH]',
    '🧪': '[TEST]',
    '🐳': '[DOCKER]',
}

for filename in files_to_fix:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for emoji, replacement in replacements.items():
            content = content.replace(emoji, replacement)
        
        if content != original:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed {filename}")
        else:
            print(f"  {filename} - no changes needed")
    except FileNotFoundError:
        print(f"  {filename} - not found")

print("\nDone!")
