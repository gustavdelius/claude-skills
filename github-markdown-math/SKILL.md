---
name: github-markdown-math
description: >-
  Write, audit and fix LaTeX math ($...$ and $$...$$) in Markdown that will be
  rendered on GitHub (READMEs, docs, issues, PRs, wikis, notes kept in a repo)
  so it does not break: equations crushed into a vertical strip by \tag,
  "macros not allowed" errors such as \operatorname, unrendered $$ blocks, and
  backslashes eaten by CommonMark. Use whenever drafting or editing
  mathematical Markdown destined for GitHub, or when GitHub shows red or
  garbled equations. Not needed for LaTeX, Pandoc, Jupyter or VS Code output.
---

# GitHub Markdown Math: Rendering Rules and Workarounds

GitHub renders Markdown math in two stages:

1. **Server side (`cmark-gfm` + math sanitizer):** finds the `$ ... $` and `$$ ... $$` boundaries, applies CommonMark backslash-unescaping to ASCII punctuation, and rejects disallowed LaTeX macros before emitting `<math-renderer>` tags.
2. **Client side (`<math-renderer>` + `MathJax.tex2mml`):** converts TeX to MathML and injects it into the page for native browser **MathML Core** layout.

Both stages have bugs that break ordinary LaTeX. The rules below are workarounds for those bugs.

## When to use this skill

- Writing or editing math in a `.md` file that will be read on GitHub.
- Fixing equations that render crushed, red, or as raw `$$` text on GitHub.
- Not needed for files that only go through LaTeX, Pandoc, Jupyter, MkDocs or VS Code. If a file is read in both places, the replacements below are ordinary TeX/MathJax, so they still render elsewhere.

## Workflow

1. While writing, follow rules 1 to 4 below.
2. Before committing, run the check script on the changed Markdown files (see [Script](#script)). Run it without `--check` to fix them in place.
3. Review the result with `git diff`. The script is regex-based, so treat its output as a draft. Rendering cannot be verified locally; if in doubt, preview on GitHub.

## Quick reference

| Instead of | Write | Why |
| --- | --- | --- |
| `\tag{2.1}` | `\qquad\text{(2.1)}` | `\tag` crushes the equation into a vertical strip |
| `\operatorname{Foo}` | `\mathrm{Foo}` | `operatorname` is blocked by the sanitizer |
| `\mathrm{Im} D_t` | `\mathrm{Im}\thinspace D_t` | restores operator spacing |
| `\hbox{...}`, `{\rm ...}` | `\text{...}`, `{\mathrm{...}}` | plain-TeX macros are blocked |
| `\{`, `\}` | `\lbrace`, `\rbrace` | CommonMark turns `\{` into `{` |
| `\\` on a single line | `\cr` | CommonMark turns `\\` into `\` |
| `\,` | `\thinspace` | CommonMark turns `\,` into `,` |
| `,\,` | `, ` | would render as a double comma |
| `q_*` (several `*` in one block) | `q_\ast` | paired `*` becomes Markdown emphasis |

---

## 1. Never use `\tag{...}` (prevents 1-character vertical crushing)

- **Bug:** `MathJax.tex2mml` serializes any equation containing `\tag{2.1}` as `<mtable displaystyle="true"><mlabeledtr><mtd>...`. The browser **MathML Core** specification removed `<mlabeledtr>`, so Chromium/Blink and Firefox do not treat it as a table row and squeeze the equation into a 1-character-wide column.
- **Workaround:** put `\qquad\text{(2.1)}` at the end of the display equation instead. For a prime in the label, use the Unicode `′` inside `\text{(3.3′)}` rather than a nested `$\tag{3.3$'$}$`.

```markdown
<!-- Broken on GitHub (crushed into a vertical column) -->
$$
\partial_t \mathcal{Q} + \partial_x \mathcal{J} = 0 \tag{2.1}
$$

<!-- Works on GitHub -->
$$
\partial_t \mathcal{Q} + \partial_x \mathcal{J} = 0 \qquad\text{(2.1)}
$$
```

---

## 2. Never use `\operatorname{...}`, `\hbox{...}` or `{\rm ...}` (prevents disallowed-macro errors)

- **Bug:** GitHub's server-side sanitizer blocks `\operatorname` and `\operatorname*` with the banner `The following macros are not allowed: operatorname`.
- **Workaround:**
  - Replace `\operatorname{Foo}` with `\mathrm{Foo}`. When it is followed directly by a letter or a backslash macro (for example `\operatorname{Im} D_t` or `\operatorname{pr} v`), add `\thinspace ` (`\mathrm{Im}\thinspace D_t`) to keep the operator spacing.
  - Replace plain-TeX `\hbox{...}` with `\text{...}`, and `{\rm ...}` with `{\mathrm{...}}`.

```markdown
<!-- Broken on GitHub ("The following macros are not allowed: operatorname") -->
$\operatorname{diag}(1, -1)$ and $\operatorname{Im} D_t$

<!-- Works on GitHub -->
$\mathrm{diag}(1, -1)$ and $\mathrm{Im}\thinspace D_t$
```

---

## 3. Make delimiters, spacing and row breaks survive CommonMark unescaping

- **Bug:** before the math reaches `<math-renderer>`, GitHub's Markdown parser applies CommonMark ASCII-punctuation unescaping inside `$ ... $` and `$$ ... $$`:
  - `\{` becomes `{` and `\}` becomes `}`. This causes `Missing or unrecognized delimiter for \left` on `\left\{`, and silently strips the braces from Poisson brackets `\{F, G\}`.
  - `\\` (when not followed by a newline) becomes `\`. This breaks single-line matrices and cases such as `\begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}` into `\-1`, giving red undefined-macro errors.
  - `,\,` becomes `,,` (a double comma) and `\,` becomes `,` (a literal comma before `dx`).
  - Paired `*` inside a math block (for example `U_+(z - 2q_*), \quad z = w + Dq_*`) can be parsed as Markdown `<em>` emphasis.
- **Workaround:**
  - Use `\lbrace` and `\rbrace` instead of `\{` and `\}` (add a space if a letter follows: `\lbrace F, G\rbrace`).
  - Use `\cr` instead of `\\` for row breaks in single-line matrices and environments, or put a newline immediately after `\\` inside multi-line `$$` ... `$$` blocks.
  - Use `\thinspace` instead of `\,` (with a trailing space before letters: `dt\thinspace dx`), and replace `,\,` with `, `.
  - Use `\ast` (`q_\ast`) instead of `*` (`q_*`) when an equation contains several asterisks.

```markdown
<!-- Broken on GitHub -->
Inline Poisson bracket $\{F, G\} = 0$, set $\left\{ x : x > 0 \right\}$, integral $\int dx\,dy$, matrix $\bigl(\begin{smallmatrix} 0 & 1 \\ -1 & 0 \end{smallmatrix}\bigr)$.

<!-- Works on GitHub -->
Inline Poisson bracket $\lbrace F, G\rbrace = 0$, set $\left\lbrace x : x > 0 \right\rbrace$, integral $\int dx\thinspace dy$, matrix $\bigl(\begin{smallmatrix} 0 & 1 \cr -1 & 0 \end{smallmatrix}\bigr)$.
```

---

## 4. Format `$$ ... $$` block boundaries for `cmark-gfm`

- **Bug:** when an equation contains several `_` or `*` characters, `cmark-gfm` fails to recognise `$$ ... $$` blocks in three situations, leaving raw `$$` text and italicising the text between underscores:
  1. Top-level `$$ ... $$` blocks without blank lines before and after.
  2. Multi-line `$$\begin{aligned} ... \end{aligned}$$` blocks where `$$` sits on the same line as `\begin{aligned}` instead of on its own line.
  3. Multi-line `$$` ... `$$` blocks indented inside list items (`1. ...` or `- ...`) or blockquotes (`> ...`).
- **Workaround:**
  - **Top-level display math:** put the opening and closing `$$` on their own lines at column 0, with a blank line before and after:

    ```markdown

    $$
    \begin{aligned}
    a &= b + c, \\
    d &= e + f.
    \end{aligned} \qquad\text{(1.1)}
    $$

    ```
  - **Display math inside list items or blockquotes:** keep the whole equation on a **single line** as `$$\displaystyle ...$$` (use `\cr` for row breaks inside environments), surrounded by blank lines:

    ```markdown
    1. Inside a numbered list item:

       $$\displaystyle S_d = \int_{\mathbb{R}} dt\thinspace \mathcal{L}_d(\phi_t, \psi_t) \qquad\text{(1.2)}$$

    ```

---

## Script

[scripts/fix_github_math.py](scripts/fix_github_math.py) applies the rules above to Markdown files. It rewrites only the contents of `$...$` and `$$...$$`, leaves fenced code and inline code alone, does not touch files without math, and is idempotent. Run it from anywhere:

```bash
# Check without modifying (exits 1 if any file needs changes; usable in CI or a pre-commit hook)
python3 ~/.claude/skills/github-markdown-math/scripts/fix_github_math.py --check path/to/file.md

# Fix in place
python3 ~/.claude/skills/github-markdown-math/scripts/fix_github_math.py path/to/file.md
```

If this skill is installed in a project instead (`.claude/skills/github-markdown-math/`), use that path.

### Limitations

- It is regex-based, so review the diff. It also cannot confirm that GitHub renders the result correctly.
- `\operatorname{...}` is converted only when its argument has no nested braces. `\thinspace` is added after `\mathrm{...}` only for a fixed list of names (`Im`, `im`, `pr`, `graph`, `Div`, `ker`, `dim`, `deg`, `span`, `spec`, `End`, `Re`, `tr`, `rank`); add it by hand for others.
- Of the asterisks, only `q_*` is rewritten to `q_\ast`; check other `*` by hand (rule 3).
- Blockquote equations are handled one level deep (`> `), not nested (`> > `).
- A line with two currency signs (`$5 and $10`) can be read as inline math. This is harmless unless the text between them contains a backslash sequence the rules rewrite.
- The rules describe GitHub's behaviour as observed. If GitHub fixes one of these bugs, the matching workaround becomes unnecessary.
