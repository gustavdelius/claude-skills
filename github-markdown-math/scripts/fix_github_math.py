#!/usr/bin/env python3
"""Audit and fix GitHub Flavored Markdown math rendering bugs in Markdown files.

Usage:
    python3 ~/.claude/skills/github-markdown-math/scripts/fix_github_math.py [--check] <file1.md> [file2.md ...]

Only the contents of $...$ and $$...$$ are rewritten (fenced code blocks and
inline code are left alone). The script is idempotent: running it twice gives
the same result as running it once.
"""

import argparse
import re
import sys


def fix_math_content(m: str, is_single_line: bool = False) -> str:
    # 1. \tag{X} -> \qquad\text{(X)}; \tag*{X} -> \qquad\text{X};
    #    nested prime \tag{3.3$'$} -> \qquad\text{(3.3′)}
    m = re.sub(r"\\tag\{([^{}$]*)\$'\$\}", r"\\qquad\\text{(\1′)}", m)
    m = re.sub(r"\\tag\*\{([^{}]+)\}", r"\\qquad\\text{\1}", m)
    m = re.sub(r"\\tag\{([^{}]+)\}", r"\\qquad\\text{(\1)}", m)

    # 2. Replace disallowed \operatorname* and \operatorname with \mathrm
    m = re.sub(r"\\operatorname\*?\s*\{([^{}]*)\}", r"\\mathrm{\1}", m)
    m = re.sub(
        r"\\mathrm\{(Im|im|pr|graph|Div|ker|dim|deg|span|spec|End|Re|tr|rank)\}[ \t]*(?!\\thinspace\b)(?=[A-Za-z]|\\[A-Za-z])",
        r"\\mathrm{\1}\\thinspace ",
        m,
    )

    # 3. Replace \hbox{...} with \text{...} and {\rm ...} with {\mathrm{...}}
    m = re.sub(r"\\hbox\s*\{([^{}]*)\}", r"\\text{\1}", m)
    m = re.sub(r"\{\\rm\s+([^{}]*)\}", r"{\\mathrm{\1}}", m)

    # 4. Replace \{ and \} with \lbrace and \rbrace (add space if followed by letter)
    m = re.sub(r"\\\{(?=[A-Za-z])", r"\\lbrace ", m)
    m = m.replace(r"\{", r"\lbrace")
    m = re.sub(r"\\\}(?=[A-Za-z])", r"\\rbrace ", m)
    m = m.replace(r"\}", r"\rbrace")

    # 5. Replace ,\, with ,  and \, with \thinspace (collapse duplicate \thinspace)
    m = m.replace(r",\, ", ", ")
    m = m.replace(r",\,", ", ")
    m = re.sub(r"\\,(?=[A-Za-z])", r"\\thinspace ", m)
    m = m.replace(r"\,", r"\thinspace")
    m = re.sub(r"(?:\\thinspace\s*){2,}", r"\\thinspace ", m)

    # 6. Replace \\ not followed by newline (or all \\ if single-line) with \cr
    if is_single_line:
        m = re.sub(r"\\\\(?![a-zA-Z])[ \t]*", r"\\cr ", m)
    else:
        m = re.sub(r"\\\\(?![a-zA-Z\s]*\n)[ \t]*", r"\\cr ", m)

    # 7. If multiple * exist in the same math block, replace q_* with q_\ast
    if m.count("*") >= 2:
        m = m.replace("q_*", r"q_\ast")

    return m


def process_markdown(orig: str) -> str:
    if "$" not in orig:
        return orig

    text = orig
    fences = []

    def save_fence(match):
        fences.append(match.group(0))
        return f"@@FENCE_{len(fences)-1}@@"

    # Fenced code blocks, including ones indented inside list items or quotes.
    text = re.sub(
        r"^[ \t>]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t>]*\1[ \t]*$",
        save_fence,
        text,
        flags=re.M | re.S,
    )

    inlines = []

    def save_inline_code(match):
        inlines.append(match.group(0))
        return f"@@INLINE_{len(inlines)-1}@@"

    text = re.sub(r"`[^`\n]+`", save_inline_code, text)

    display_blocks = []

    def save_display_math(match):
        indent = match.group(2)
        body = match.group(3).strip()
        exact = False
        if indent:
            if ">" in indent:
                lines = [re.sub(r"^[ \t]*>?[ \t]*", "", ln) for ln in body.split("\n")]
                body = " ".join(ln.strip() for ln in lines if ln.strip())
            body_single = re.sub(r"\s*\n\s*", " ", body)
            body_single = fix_math_content(body_single, is_single_line=True)
            if not body_single.startswith(r"\displaystyle"):
                body_single = r"\displaystyle " + body_single
            if ">" in indent:
                block_str = f"\n{indent}$${body_single}$$"
                exact = True
            else:
                block_str = f"\n\n{indent}$${body_single}$$\n\n"
        else:
            body_fixed = fix_math_content(body, is_single_line=False)
            block_str = f"\n\n$$\n{body_fixed}\n$$\n\n"
        idx = len(display_blocks)
        display_blocks.append((block_str, exact))
        return f"@@DISPLAY_{idx}@@"

    text = re.sub(
        r"(\n|^)([ \t]*>?[ \t]*)\$\$([\s\S]*?)\$\$[ \t]*(?=\n|$)",
        save_display_math,
        text,
    )

    def replace_inline_math(match):
        inner = fix_math_content(match.group(1), is_single_line=True)
        return f"${inner}$"

    text = re.sub(r"(?<!\$)\$(?!\$)([^\n$]+?)(?<!\$)\$(?!\$)", replace_inline_math, text)

    for i, (b, exact) in enumerate(display_blocks):
        if exact:
            text = text.replace(f"@@DISPLAY_{i}@@", b)
        else:
            # The block carries its own surrounding blank lines, so swallow the old ones.
            text = re.sub(rf"\n*@@DISPLAY_{i}@@\n*", lambda _m, b=b: b, text)
    for i, c in enumerate(inlines):
        text = text.replace(f"@@INLINE_{i}@@", c)
    for i, f in enumerate(fences):
        text = text.replace(f"@@FENCE_{i}@@", f)

    # Trim only what the display blocks may have added at the file edges.
    if not orig.startswith("\n"):
        text = text.lstrip("\n")
    text = text.rstrip("\n") + ("\n" if orig.endswith("\n") else "")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check files without modifying")
    parser.add_argument("files", nargs="+", help="Markdown files to check or fix")
    args = parser.parse_args()

    needs_changes = 0
    for path in args.files:
        with open(path, "r", encoding="utf-8") as fh:
            orig = fh.read()
        fixed = process_markdown(orig)
        if fixed != orig:
            needs_changes += 1
            if args.check:
                print(f"FAIL: {path} requires GitHub math formatting fixes")
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(fixed)
                print(f"PASS: Updated {path}")
        else:
            print(f"PASS: {path}")

    return 1 if (args.check and needs_changes > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
