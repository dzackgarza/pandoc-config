# Markdown Authoring Style

Formatting conventions for markdown compiled through this configuration.
Written for the dissertation's sections and applying to every prose project
built with `compile-pandoc` or `compile-pandoc-project`.

## 1. Fenced Divs

### Standard Format
All fenced divs must use the following format:

```markdown
:::{.envname title="Some Title"}
Text content here.
:::
```

### With Labels
When labels are needed, place them on their own line immediately after the opening:

```markdown
:::{.theorem title="Main Result"}
\label{thm:main_result}
The statement of the theorem goes here.
:::
```

### Alternative Labeling
You may also use pandoc-style labeling syntax or rely on auto-labeling with comments:

```markdown
:::{.theorem title="Main Result" #thm:main-result}
The statement of the theorem goes here.
:::
```

### Forbidden Syntax
The following syntax is **NOT ALLOWED**:

```markdown
::: remark
```

Always include the title attribute and proper class syntax.

## 2. Display Mathematics

### Standard Format
All display math must use the `align*` environment with specific formatting:

```latex

\begin{align}
f(x) &= 3x + 2
\\
     &= 3(x + {2 \over 3})
\\
     &= 3x + 2
.\end{align}

```

### Key Requirements

1. **Spacing**: Always include at least one blank line before and after the math block

2. **Alignment**: All ampersands (`&`) must be visually aligned in the source

3. **Line breaks**: The `\\` symbols should be on their own lines for clarity

4. **Left alignment**: The `\begin{align}` and `\end{align}` lines should be flush left (no indentation)

5. **Content separation**: Keep mathematical content separate from LaTeX coding for better diff visibility

6. **No indentation**: Do not indent the contents inside align environments

### Example with Multiple Steps

```latex

\begin{align}
\int_0^1 x^2 \, dx &= \left[ {x^3 \over 3} \right]_0^1
\\
                   &= {1^3 \over 3} - {0^3 \over 3}
\\
                   &= {1 \over 3}
.\end{align}

```

## 3. Forbidden Math Environments

### Replace \[ \] with align*
**Never use** `\[` and `\]` for display math. Always use `align*`:

❌ **Incorrect:**
```latex
\[
f(x) = x^2
\]
```

✅ **Correct:**
```latex

\begin{align}
f(x) &= x^2
.\end{align}

```

### Don't Use `aligned`
Avoid the `aligned` environment entirely. Use `align*` instead.

## 4. Complex Alignments

### One Ampersand Rule
Use at most one `&` per line in align environments. For more complex alignments, switch to `tabular` or `array` environments:

❌ **Too many ampersands:**
```latex
\begin{align}
a &= b &= c &= d \\
e &= f &= g &= h
\end{align}
```

✅ **Use array instead:**
```latex

\begin{array}{cccc}
a = b &= c &= d \\
e = f &= g &= h
\end{array}

```

## 5. Lists

### List Spacing
All list items must be separated by at least one blank line:

✅ **Correct:**
```markdown
1. First item with some content.

2. Second item with more content.

3. Third item with additional details.
```

❌ **Incorrect:**
```markdown
1. First item
2. Second item
3. Third item
```

### Nested Lists
For nested lists, maintain the spacing rule:

```markdown
1. Main item one.

   a. Sub-item one.
   
   b. Sub-item two.

2. Main item two.

   - Bullet sub-item.
   
   - Another bullet sub-item.
```

## 6. Additional Formatting Rules

### Section Headers
Use standard markdown headers with proper spacing:

```markdown
## Main Section

Content here.

### Subsection

More content.
```

### Code Blocks
Use proper syntax highlighting when applicable:

```python
def example_function():
    return "Hello, world!"
```

### Citations
Use standard LaTeX citation format:
```markdown
As shown in \cite{author2023}, the result follows.
```

## Enforcement

Apply these rules when writing new content or reviewing existing files.
`just pandoc::format-md <dir>` enforces the mechanical part: one sentence per
line and list spacing. The rest is a reading standard, not a checked one.
