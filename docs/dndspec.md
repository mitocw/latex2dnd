# dndspec — Simplified DND Problem Specification

`dndspec` is a plain-text format for defining edX drag-and-drop problems without
writing LaTeX by hand.  A `.dndspec` file is compiled by `latex2dnd` into a `.tex`
file, then processed normally to produce the XML and PNG assets.

```
latex2dnd problem.dndspec
```

---

## File format overview

A `.dndspec` file consists of keyword lines and two kinds of multi-line blocks.
Lines starting with `%` or `#` are comments.  Blank lines are ignored.
Keywords are case-sensitive and must start at column 0 (no leading spaces).

```
% This is a comment
MATCH_LABELS: G, m_1, m_2, R
BEGIN_EXPRESSION
\bea
    \frac{ G m_1 m_2 }{ R }
\nonumber
\eea
END_EXPRESSION
CHECK_FORMULA: G * m_1 * m_2 / R
```

---

## Keywords

### Labels

**`MATCH_LABELS: <label>, <label>, ...`**  
Labels that appear in the expression and become drop-target boxes.  Each label
must appear in the expression surrounded by spaces so the parser can locate it.
May be specified more than once; all lists are concatenated.

**`DISTRACTOR_LABELS: <label>, <label>, ...`**  
Additional labels shown as draggables that are *not* correct answers.
May be specified more than once.

**`ALL_LABELS: <label>, <label>, ...`**  
The complete ordered list of draggable labels to display (both match and
distractor).  Controls display order.  If omitted, defaults to
`MATCH_LABELS` + `DISTRACTOR_LABELS`.  May be specified more than once;
lists are concatenated, which is useful for long label sets:

```
ALL_LABELS: \frac{|g\>+|e\>}{\sqrt{2}}, \frac{|g\>-|e\>}{\sqrt{2}}
ALL_LABELS: |g\>, |e\>
```

**`MATH_EXP: <label>, <math_expression>`**  
Override the auto-generated math expression for a label.  Useful when the
label contains text or complex LaTeX that cannot be parsed automatically.
May be used multiple times, once per label:

```
MATH_EXP: Gravity Constant, G
MATH_EXP: Mass One, m
```

---

### Expression block

```
BEGIN_EXPRESSION
  <LaTeX expression with MATCH_LABELS embedded>
END_EXPRESSION
```

The LaTeX expression for the problem.  Every match label must appear
**surrounded by spaces** so the parser can replace it with the appropriate
`\DDbox`.  Standard LaTeX math environments (`equation`, `eqnarray`, etc.)
work inside this block.

---

### Formula checking

**`CHECK_FORMULA: <formula>`**  
A text-based math formula representing the correct answer, using the
*math expression* form of each label (not the LaTeX form).  Variables are
sampled numerically to verify equivalence.

```
CHECK_FORMULA: G * m_1 * m_2 / R
```

**`CHECK_FORMULA_BOXES: <formula using [#]>`**  
Manually specify which box index (`[1]`, `[2]`, …) maps to which position in
the formula.  Only needed when the same match label appears in more than one
drop target.

**`TEST_CORRECT: <formula>`**  
A formula that should evaluate as correct.  Generates a `\DDtest{correct}{…}`
assertion.  May be used multiple times.

**`TEST_INCORRECT: <formula>`**  
A formula that should evaluate as incorrect.  Generates a `\DDtest{incorrect}{…}`
assertion.  May be used multiple times.

---

### Layout and display

**`BOX_WIDTH: <dimension>`**  
Width of each drop-target box.  Default: `8ex`.

**`BOX_HEIGHT: <dimension>`**  
Height of each drop-target box.  Default: `4ex`.

**`RESOLUTION: <dpi>`**  
Resolution of generated PNG files in DPI.  Default: `300`.
Can be set to `max` to auto-scale.

**`OPTIONS: <option string>`**  
Pass options to `\DDoptions{}`.  Common values:
- `HIDE_FORMULA_INPUT` — hide the formula input field (default)
- `ALLOW_EMPTY` — allow empty boxes in submission
- `CAN_REUSE` — allow a draggable to be used more than once
- `NO_MATH` — suppress `$…$` wrapping around label contents

**`FEEDBACK: <text>`**  
Feedback string shown to students.  Generates `\DDfeedback{…}`.

**`NAME: <name>`**  
Problem name.

**`TITLE: <title>`**  
Problem title.

---

### LaTeX preamble

**`EXTRA_HEADER_TEX: <latex line>`**  
Insert a single line into the generated document preamble (after
`\usepackage{amsmath}`, before `\input{latex2dnd}`).  May be used multiple
times, once per line:

```
EXTRA_HEADER_TEX: \usepackage{tikz}
EXTRA_HEADER_TEX: \usepackage{amsfonts}
```

**`BEGIN_EXTRA_HEADER_TEX` / `END_EXTRA_HEADER_TEX`**  
Multi-line alternative to `EXTRA_HEADER_TEX:` for inserting several lines of
preamble cleanly:

```
BEGIN_EXTRA_HEADER_TEX
\usepackage{tikz}
\usepackage{amsfonts}
\newcommand{\ket}[1]{\left\vert #1 \right\rangle}
END_EXTRA_HEADER_TEX
```

Both forms may be combined in the same file; their contributions are
concatenated in the order they appear.

---

### Delimiter

**`DELIMETER: <character>`**  
Change the separator used in `MATCH_LABELS`, `DISTRACTOR_LABELS`, and
`ALL_LABELS`.  Default is `,`.  Use this when labels themselves contain
commas (e.g. `m_{1,2}`):

```
DELIMETER: ;
MATCH_LABELS: G; m_{1,2}; R
```

---

## Complete examples

### Minimal — gravity formula, no checking

```
MATCH_LABELS: G, m_1, m_2, R
BEGIN_EXPRESSION
\bea
    \frac{ G m_1 m_2 }{ R }
\nonumber
\eea
END_EXPRESSION
```

### With distractors and formula checking

```
% Newton's law of gravitation
MATCH_LABELS: m_1 m_2, r
ALL_LABELS: m_1, m_2, m_1 m_2, m_1^2 m_2, r, r^2

BEGIN_EXPRESSION
\begin{equation}
    F = \frac{ G m_1 m_2 }{ r }
\nonumber
\end{equation}
END_EXPRESSION

CHECK_FORMULA: m_1 * m_2 / r
TEST_CORRECT:  m_2 * m_1 / r
TEST_INCORRECT: m_1 * m_2 / r^2
```

### Custom label text via MATH_EXP

When labels are English phrases rather than math symbols, use `MATH_EXP` to
provide the symbolic form for formula checking:

```
MATCH_LABELS: Gravity Constant, Mass One, R
ALL_LABELS: Gravity Constant, Mass One, Mass Two, R
MATH_EXP: Gravity Constant, G
MATH_EXP: Mass One, m
MATH_EXP: Mass Two, m

BEGIN_EXPRESSION
\bea
    \frac{ Gravity Constant { Mass One } }{ R }
\nonumber
\eea
END_EXPRESSION

CHECK_FORMULA: G * m / R
```

### Image annotation with extra preamble packages

```
BEGIN_EXTRA_HEADER_TEX
\usepackage[bwr]{callouts}
END_EXTRA_HEADER_TEX

BOX_WIDTH: 11ex
BOX_HEIGHT: 6ex
MATCH_LABELS: \frac{|g\>+|e\>}{\sqrt{2}}, |g\>
ALL_LABELS: \frac{|g\>+|e\>}{\sqrt{2}}, \frac{|g\>-|e\>}{\sqrt{2}}
ALL_LABELS: \frac{|g\>+i |e\>}{\sqrt{2}}, \frac{|g\>-i|e\>}{\sqrt{2}}, |g\>, |e\>

BEGIN_EXPRESSION
\begin{center}
  \begin{annotate}{\includegraphics[width=0.41\textwidth]{figure.png}}{0.56}
    \note{2.9,2.5}{ \frac{|g\>+|e\>}{\sqrt{2}} }
  \end{annotate}
\end{center}
END_EXPRESSION
```

---

## How dndspec compiles to LaTeX

The `.dndspec` file is compiled to a `.tex` file using the template in
`latex2dnd/tex/dndspec_template.tex`.  In that template:

- `MATCH_LABELS` → `\DDlabel[math_exp]{draggable_id}{$label_tex$}` per label
- Each label in `BEGIN_EXPRESSION` → `\DDbox{n}{width}{height}{draggable_id}`
- `CHECK_FORMULA` → `\DDformula{boxes}{samples}{expected}{}`
- `TEST_CORRECT` / `TEST_INCORRECT` → `\DDtest{correct|incorrect}{targets}{draggables}`
- `BEGIN_EXTRA_HEADER_TEX` / `EXTRA_HEADER_TEX:` → inserted verbatim before `\input{latex2dnd}`

The intermediate `.tex` file is retained alongside the outputs and can be
edited directly for customizations that go beyond what dndspec supports.

---

## Tips

- Every match label in `BEGIN_EXPRESSION` must be surrounded by spaces.
- Label text becomes the draggable ID after stripping non-alphanumeric
  characters, so `m_1` becomes `mone`, `B^\prime` becomes `Bprime`, etc.
  Use `MATH_EXP` to override when the auto-generated form is wrong.
- Use `DELIMETER: ;` whenever any label contains a comma.
- `ALL_LABELS` controls display order; put the most tempting distractors
  near the correct answers.
- The generated `.tex` file is a useful starting point for problems that
  need fine-grained layout control beyond what dndspec provides.
