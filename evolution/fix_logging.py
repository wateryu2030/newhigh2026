#!/usr/bin/env python3
"""
Fix logging f-string issues in Python files.
Converts f-string logging to lazy % formatting.
"""

import re
import sys
from pathlib import Path

def fix_logging_fstrings(content: str) -> str:
    """Convert logger.info(f"...") to logger.info("...", ...)."""
    
    # Pattern for logger.XXX(f"...{var}...")
    # This is simplified - handles common cases
    patterns = [
        # logger.info(f"text {var} text") -> logger.info("text %s text", var)
        (r'self\.logger\.info\(f"([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.info("\1%s\3", \2)'),
        (r'self\.logger\.warning\(f"([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.warning("\1%s\3", \2)'),
        (r'self\.logger\.error\(f"([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.error("\1%s\3", \2)'),
        # Multiple variables - simplified handling
        (r'self\.logger\.info\(f"([^"]*?)\{(\w+)\}([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.info("\1%s\3%s\5", \2, \4)'),
        (r'self\.logger\.warning\(f"([^"]*?)\{(\w+)\}([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.warning("\1%s\3%s\5", \2, \4)'),
        (r'self\.logger\.error\(f"([^"]*?)\{(\w+)\}([^"]*?)\{(\w+)\}([^"]*?)"\)', r'self.logger.error("\1%s\3%s\5", \2, \4)'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def fix_trailing_whitespace(content: str) -> str:
    """Remove trailing whitespace."""
    lines = content.split('\n')
    fixed_lines = [line.rstrip() for line in lines]
    return '\n'.join(fixed_lines)

def fix_unused_imports(content: str) -> str:
    """Remove unused imports (simple heuristic)."""
    # Remove 'Optional' from typing imports if present
    content = re.sub(r',\s*Optional', '', content)
    content = re.sub(r'Optional,\s*', '', content)
    # Remove 'List' from typing imports if present  
    content = re.sub(r',\s*List', '', content)
    content = re.sub(r'List,\s*', '', content)
    return content

def main():
    if len(sys.argv) < 2:
        print("Usage: fix_logging.py <file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
    
    content = filepath.read_text(encoding='utf-8')
    
    # Apply fixes
    content = fix_logging_fstrings(content)
    content = fix_trailing_whitespace(content)
    content = fix_unused_imports(content)
    
    # Write back
    filepath.write_text(content, encoding='utf-8')
    print(f"Fixed: {filepath}")

if __name__ == "__main__":
    main()
