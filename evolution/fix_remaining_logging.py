#!/usr/bin/env python3
"""Fix remaining logging f-string issues"""

from pathlib import Path
import re

def fix_file(filepath: Path):
    content = filepath.read_text(encoding='utf-8')
    
    # Fix multi-line f-string logging
    # Pattern: self.logger.info(\n    f"..."
    content = re.sub(
        r'self\.logger\.info\(\s+f"([^"]*?)\{([^}]+)\}([^"]*?)\{([^}]+)\}([^"]*?)"\s*\)',
        r'self.logger.info("\1%s\3%s\5", \2, \4)',
        content,
        flags=re.MULTILINE
    )
    
    # Fix single-line f-string logging with .error
    content = re.sub(
        r'self\.logger\.error\(f"([^"]*?)\{([^}]+)\}([^"]*?)"(, exc_info=True)?\)',
        lambda m: f'self.logger.error("{m.group(1)}%s{m.group(3)}", {m.group(2)}{m.group(4) or ""})',
        content
    )
    
    # Fix single-line f-string logging with .info
    content = re.sub(
        r'self\.logger\.info\(f"([^"]*?)\{([^}]+)\}([^"]*?)"\)',
        lambda m: f'self.logger.info("{m.group(1)}%s{m.group(3)}", {m.group(2)})',
        content
    )
    
    filepath.write_text(content, encoding='utf-8')
    print(f"Fixed: {filepath}")

# Fix notification.py
fix_file(Path("strategy-engine/src/strategies/daily_stock_analysis/notification.py"))
