"""YAML syntax error detection and auto-fix for pyqual.

This module provides syntax-level auto-fix capabilities for common YAML errors
without requiring LLM. It handles indentation, quotes, brackets, and other
common syntax mistakes with detailed error reporting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class YamlErrorType(str, Enum):
    """Types of YAML syntax errors we can detect and fix."""
    INDENTATION = "indentation"          # Mixed tabs/spaces, wrong level
    UNCLOSED_QUOTE = "unclosed_quote"    # Missing closing quote
    UNCLOSED_BRACKET = "unclosed_bracket"  # Missing ] or }
    MISSING_COLON = "missing_colon"      # Missing : after key
    DUPLICATE_KEY = "duplicate_key"      # Same key defined twice
    TRAILING_SPACE = "trailing_space"    # Spaces at end of line
    TAB_CHARACTER = "tab_character"        # Tab instead of spaces
    INVALID_ESCAPE = "invalid_escape"    # Invalid escape sequence
    BOM = "bom"                          # Byte order mark at start


@dataclass
class YamlSyntaxIssue:
    """A single YAML syntax issue with location and fix information."""
    line: int
    column: int
    error_type: YamlErrorType
    message: str
    original: str = ""
    fixed: str = ""
    can_fix: bool = False
    context: str = ""  # Surrounding lines for context


@dataclass
class YamlFixResult:
    """Result of parsing/fixing YAML."""
    issues: list[YamlSyntaxIssue] = field(default_factory=list)
    fixed_content: str = ""
    original_content: str = ""
    parseable: bool = False
    was_fixed: bool = False

    @property
    def fixable_issues(self) -> list[YamlSyntaxIssue]:
        return [i for i in self.issues if i.can_fix]

    @property
    def unfixable_issues(self) -> list[YamlSyntaxIssue]:
        return [i for i in self.issues if not i.can_fix]


def _detect_indentation_issues(lines: list[str]) -> list[YamlSyntaxIssue]:
    """Detect indentation problems: tabs, inconsistent spacing."""
    issues = []
    indent_sizes: list[int] = []

    for i, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Check for tabs
        if "\t" in line:
            # Find the position of the first tab
            col = line.index("\t") + 1
            # Replace tabs with 2 spaces (common YAML convention)
            fixed_line = line.replace("\t", "  ")
            issues.append(YamlSyntaxIssue(
                line=i,
                column=col,
                error_type=YamlErrorType.TAB_CHARACTER,
                message=f"Line {i}: Tab character found (use spaces for indentation)",
                original=line,
                fixed=fixed_line,
                can_fix=True,
                context=_get_context(lines, i),
            ))
            continue

        # Track indentation sizes
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            if indent > 0 and indent not in indent_sizes:
                indent_sizes.append(indent)

    # Check for inconsistent indentation (more than 2 different sizes)
    if len(indent_sizes) > 2:
        issues.append(YamlSyntaxIssue(
            line=0,
            column=0,
            error_type=YamlErrorType.INDENTATION,
            message=f"Inconsistent indentation detected ({len(indent_sizes)} different sizes). Common sizes: {sorted(indent_sizes)[:3]}",
            original="",
            fixed="",
            can_fix=False,
        ))

    return issues


def _detect_quote_issues(lines: list[str]) -> list[YamlSyntaxIssue]:
    """Detect unclosed quotes in YAML values."""
    issues = []

    for i, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Check for unclosed single quotes
        single_count = line.count("'") - line.count("\\'")
        if single_count % 2 == 1:
            # Check if it's part of a multiline (next lines might continue)
            is_multiline = _is_multiline_quote(lines, i, "'")
            if not is_multiline:
                issues.append(YamlSyntaxIssue(
                    line=i,
                    column=line.find("'") + 1,
                    error_type=YamlErrorType.UNCLOSED_QUOTE,
                    message=f"Line {i}: Unclosed single quote",
                    original=line,
                    fixed=line + "'",
                    can_fix=True,
                    context=_get_context(lines, i),
                ))

        # Check for unclosed double quotes
        double_count = line.count('"') - line.count('\\"')
        if double_count % 2 == 1:
            is_multiline = _is_multiline_quote(lines, i, '"')
            if not is_multiline:
                issues.append(YamlSyntaxIssue(
                    line=i,
                    column=line.find('"') + 1,
                    error_type=YamlErrorType.UNCLOSED_QUOTE,
                    message=f"Line {i}: Unclosed double quote",
                    original=line,
                    fixed=line + '"',
                    can_fix=True,
                    context=_get_context(lines, i),
                ))

    return issues


def _is_multiline_quote(lines: list[str], start_line: int, quote_char: str) -> bool:
    """Check if an unclosed quote is actually a multiline string."""
    if start_line >= len(lines):
        return False

    # Look ahead for closing quote within reasonable distance
    for i in range(start_line, min(start_line + 10, len(lines))):
        if lines[i].rstrip().endswith(quote_char):
            return True
        # If we see a new key or list item, it's not multiline
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            if re.match(r'^\w+:', stripped) or stripped.startswith("- "):
                return False

    return False


def _detect_bracket_issues(lines: list[str]) -> list[YamlSyntaxIssue]:
    """Detect unclosed brackets in flow style YAML."""
    issues = []
    bracket_stack: list[tuple[str, int, int]] = []  # (char, line, col)

    bracket_pairs = {"[": "]", "{": "}", "(": ")"}
    closing = set(bracket_pairs.values())

    for i, line in enumerate(lines, 1):
        for j, char in enumerate(line, 1):
            if char in bracket_pairs:
                bracket_stack.append((char, i, j))
            elif char in closing:
                if bracket_stack:
                    opening, _, _ = bracket_stack[-1]
                    expected_close = bracket_pairs.get(opening, "")
                    if char == expected_close:
                        bracket_stack.pop()
                    else:
                        # Mismatched brackets
                        issues.append(YamlSyntaxIssue(
                            line=i,
                            column=j,
                            error_type=YamlErrorType.UNCLOSED_BRACKET,
                            message=f"Line {i}: Mismatched bracket, expected '{expected_close}' but found '{char}'",
                            original=line,
                            fixed=line,  # Can't auto-fix mismatched
                            can_fix=False,
                            context=_get_context(lines, i),
                        ))

    # Report unclosed brackets
    for opening, line_num, col_num in bracket_stack:
        closing_char = bracket_pairs[opening]
        original = lines[line_num - 1] if line_num <= len(lines) else ""
        fixed = original + closing_char

        issues.append(YamlSyntaxIssue(
            line=line_num,
            column=col_num,
            error_type=YamlErrorType.UNCLOSED_BRACKET,
            message=f"Line {line_num}: Unclosed '{opening}' bracket",
            original=original,
            fixed=fixed,
            can_fix=True,
            context=_get_context(lines, line_num),
        ))

    return issues


def _detect_colon_issues(lines: list[str]) -> list[YamlSyntaxIssue]:
    """Detect missing colons after keys."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check if line looks like a key but missing colon
        # Pattern: word at start followed by space and value, but no colon
        if re.match(r'^\w+\s+[^#\s:]+', stripped):
            # Check it's not a list item or already has a colon
            if not stripped.startswith("-") and ":" not in stripped.split()[0]:
                key_match = re.match(r'^(\w+)\s+(.+)$', stripped)
                if key_match:
                    key, value = key_match.groups()
                    fixed = line.replace(key, f"{key}:", 1)
                    issues.append(YamlSyntaxIssue(
                        line=i,
                        column=len(line) - len(stripped) + len(key),
                        error_type=YamlErrorType.MISSING_COLON,
                        message=f"Line {i}: Possible missing colon after key '{key}'",
                        original=line,
                        fixed=fixed,
                        can_fix=True,
                        context=_get_context(lines, i),
                    ))

    return issues


def _detect_trailing_spaces(lines: list[str]) -> list[YamlSyntaxIssue]:
    """Detect trailing whitespace."""
    issues = []

    for i, line in enumerate(lines, 1):
        if line.rstrip() != line:
            issues.append(YamlSyntaxIssue(
                line=i,
                column=len(line.rstrip()) + 1,
                error_type=YamlErrorType.TRAILING_SPACE,
                message=f"Line {i}: Trailing whitespace",
                original=line,
                fixed=line.rstrip(),
                can_fix=True,
                context="",
            ))

    return issues


def _detect_bom(content: str) -> list[YamlSyntaxIssue]:
    """Detect byte order mark at start of file."""
    issues = []

    if content.startswith("\ufeff"):
        issues.append(YamlSyntaxIssue(
            line=1,
            column=1,
            error_type=YamlErrorType.BOM,
            message="File starts with UTF-8 BOM (Byte Order Mark)",
            original=content[:10],
            fixed=content[1:10],
            can_fix=True,
            context="",
        ))

    return issues


def _get_context(lines: list[str], line_num: int, context_size: int = 2) -> str:
    """Get surrounding lines for context."""
    start = max(0, line_num - context_size - 1)
    end = min(len(lines), line_num + context_size)
    context_lines = []
    for i in range(start, end):
        marker = ">>> " if i == line_num - 1 else "    "
        context_lines.append(f"{marker}{i+1:3}: {lines[i]}")
    return "\n".join(context_lines)


def analyze_yaml_syntax(content: str) -> YamlFixResult:
    """Analyze YAML content for syntax errors without external parsers.

    Returns detailed issues with locations and auto-fix suggestions.
    """
    lines = content.splitlines()
    issues: list[YamlSyntaxIssue] = []

    # Run all detectors
    issues.extend(_detect_indentation_issues(lines))
    issues.extend(_detect_quote_issues(lines))
    issues.extend(_detect_bracket_issues(lines))
    issues.extend(_detect_colon_issues(lines))
    issues.extend(_detect_trailing_spaces(lines))
    issues.extend(_detect_bom(content))

    # Sort by line number
    issues.sort(key=lambda x: (x.line, x.column))

    # Try to parse with PyYAML to check if there are additional errors
    parseable, parse_error = _try_parse_yaml(content)

    # If PyYAML reports an error we didn't catch, add it
    if not parseable and parse_error:
        yaml_error = _parse_pyyaml_error(parse_error, lines)
        if yaml_error and not any(i.line == yaml_error.line for i in issues):
            issues.append(yaml_error)

    # Generate fixed content
    fixed_lines = lines.copy()
    for issue in sorted(issues, key=lambda x: x.line, reverse=True):
        if issue.can_fix and 1 <= issue.line <= len(fixed_lines):
            fixed_lines[issue.line - 1] = issue.fixed

    return YamlFixResult(
        issues=issues,
        fixed_content="\n".join(fixed_lines),
        original_content=content,
        parseable=parseable,
        was_fixed=any(i.can_fix for i in issues),
    )


def _try_parse_yaml(content: str) -> tuple[bool, str]:
    """Try to parse YAML and return success status and error message."""
    try:
        import yaml
        yaml.safe_load(content)
        return True, ""
    except Exception as e:
        return False, str(e)


def _parse_pyyaml_error(error_str: str, lines: list[str]) -> YamlSyntaxIssue | None:
    """Parse PyYAML error message to extract line/column info."""
    # Common patterns in PyYAML errors
    patterns = [
        r'line (\d+), column (\d+)',
        r'line (\d+)',
        r'position (\d+)',
    ]

    line_num = 1
    col_num = 1

    for pattern in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            if 'column' in pattern:
                line_num = int(match.group(1))
                col_num = int(match.group(2))
            else:
                line_num = int(match.group(1))
            break

    # Determine error type from message
    error_type = YamlErrorType.INDENTATION
    if "mapping" in error_str.lower():
        error_type = YamlErrorType.MISSING_COLON
    elif "quote" in error_str.lower():
        error_type = YamlErrorType.UNCLOSED_QUOTE

    context = _get_context(lines, line_num) if line_num <= len(lines) else ""

    return YamlSyntaxIssue(
        line=line_num,
        column=col_num,
        error_type=error_type,
        message=f"Parser error: {error_str}",
        original=lines[line_num - 1] if 1 <= line_num <= len(lines) else "",
        fixed="",
        can_fix=False,
        context=context,
    )


def fix_yaml_file(config_path: Path, dry_run: bool = False) -> YamlFixResult:
    """Analyze and optionally fix a YAML file.

    Args:
        config_path: Path to YAML file
        dry_run: If True, don't write changes, just analyze

    Returns:
        YamlFixResult with issues and fixed content
    """
    content = config_path.read_text(encoding="utf-8")
    result = analyze_yaml_syntax(content)

    if result.was_fixed and not dry_run:
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        backup_path.write_text(content, encoding="utf-8")
        config_path.write_text(result.fixed_content, encoding="utf-8")

    return result
