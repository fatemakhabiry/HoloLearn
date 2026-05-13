import io
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

from reportlab.platypus import Image as RLImage

# Configure matplotlib for better equation rendering
rcParams['mathtext.fontset'] = 'cm'
rcParams['mathtext.rm'] = 'serif'


# Markdown → plain-text helpers

def strip_markdown(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{3}(.+?)\*{3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_{3}(.+?)_{3}',   r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*{2}(.+?)\*{2}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_{2}(.+?)_{2}',   r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_(.+?)_',   r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


# LaTeX pre-processor

def fix_latex(expr: str) -> str:
    e = expr
    e = re.sub(r'\^(\([^)]+\))', r'^{\1}', e)
    e = re.sub(r'\^(\d{2,})', r'^{\1}', e)
    e = re.sub(r'_(\d{2,})',  r'_{\1}', e)
    greek = (r'alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|'
             r'nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|'
             r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega')
    e = re.sub(rf'\\({greek})([a-zA-Z])\b', r'\\\1_\2', e)
    e = re.sub(r'\bh\\theta\b', r'h_{\\theta}', e)
    e = re.sub(r'\bh_\\theta\b', r'h_{\\theta}', e)
    e = re.sub(r'\bx([ijklmn])\b', r'x_\1', e)
    e = re.sub(r'\by([ijklmn])\b', r'y_\1', e)
    e = re.sub(r'\\(sum|prod|int)\{([^}]+)\}', r'\\\1_{\2}', e)
    e = re.sub(r'(\\(?:sum|prod|int)\^)([a-zA-Z0-9])(?=[^{]|$)', r'\1{\2}', e)
    e = re.sub(r'(\\(?:sum|prod|int)_\{[^}]+\}\^)([a-zA-Z0-9])(?=[^{]|$)', r'\1{\2}', e)
    e = re.sub(r'\\frac\s+([^\s{\\]+)\s+([^\s{\\]+)', r'\\frac{\1}{\2}', e)
    e = re.sub(r'\s*\n\s*', ' ', e)
    e = re.sub(r'  +', ' ', e)
    return e.strip()


# LaTeX → PNG → ReportLab Image

def latex_to_image(latex_expr: str, fontsize: int = 14) -> io.BytesIO | None:
    stripped = latex_expr.strip()
    stripped = re.sub(r'^\$\$(.+?)\$\$$', r'\1', stripped, flags=re.DOTALL)
    stripped = re.sub(r'^\$(.+?)\$$',     r'\1', stripped, flags=re.DOTALL)
    stripped = stripped.strip()
    stripped = fix_latex(stripped)
    expr = "$" + stripped + "$"

    try:
        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        ax.set_axis_off()
        fig.patch.set_alpha(0)
        t = ax.text(0.5, 0.5, expr, fontsize=fontsize, ha='center', va='center',
                    transform=ax.transAxes, usetex=False)
        fig.canvas.draw()
        bbox = t.get_window_extent(renderer=fig.canvas.get_renderer())
        dpi = fig.dpi
        width_in  = (bbox.width  + 20) / dpi
        height_in = (bbox.height + 10) / dpi
        fig.set_size_inches(width_in, height_in)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight',
                    pad_inches=0.05, dpi=dpi, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"LaTeX rendering failed: {e}")
        plt.close('all')
        return None


# Equation normalizer
# Maps Unicode math characters to their LaTeX equivalents
_UNICODE_TO_LATEX: dict[str, str] = {
    'α': r'\alpha',   'β': r'\beta',    'γ': r'\gamma',   'δ': r'\delta',
    'ε': r'\epsilon', 'ζ': r'\zeta',    'η': r'\eta',     'θ': r'\theta',
    'ι': r'\iota',    'κ': r'\kappa',   'λ': r'\lambda',  'μ': r'\mu',
    'ν': r'\nu',      'ξ': r'\xi',      'π': r'\pi',      'ρ': r'\rho',
    'σ': r'\sigma',   'τ': r'\tau',     'υ': r'\upsilon', 'φ': r'\phi',
    'χ': r'\chi',     'ψ': r'\psi',     'ω': r'\omega',
    'Γ': r'\Gamma',   'Δ': r'\Delta',   'Θ': r'\Theta',   'Λ': r'\Lambda',
    'Ξ': r'\Xi',      'Π': r'\Pi',      'Σ': r'\Sigma',   'Υ': r'\Upsilon',
    'Φ': r'\Phi',     'Ψ': r'\Psi',     'Ω': r'\Omega',
    '∑': r'\sum',     '∏': r'\prod',    '∫': r'\int',     '∂': r'\partial',
    '∇': r'\nabla',   '∞': r'\infty',   '√': r'\sqrt',
    '≤': r'\leq',     '≥': r'\geq',     '≠': r'\neq',
    '≈': r'\approx',  '≡': r'\equiv',   '∝': r'\propto',
    '∈': r'\in',      '∉': r'\notin',   '⊂': r'\subset',  '⊃': r'\supset',
    '∩': r'\cap',     '∪': r'\cup',
    '→': r'\rightarrow',  '←': r'\leftarrow',   '↔': r'\leftrightarrow',
    '⇒': r'\Rightarrow',  '⇐': r'\Leftarrow',   '⇔': r'\Leftrightarrow',
    '·': r'\cdot',    '×': r'\times',   '÷': r'\div',
    '±': r'\pm',      '∓': r'\mp',
    '∀': r'\forall',  '∃': r'\exists',
    '⟨': r'\langle',  '⟩': r'\rangle',
}

# Matches already-delimited math regions: $$...$$ or $...$
_DELIMITED_MATH_RE = re.compile(
    r'\$\$(?:(?!\$\$).)+?\$\$'   # display math  $$...$$
    r'|\$(?!\$)[^$\n]+?\$',       # inline math   $...$
    re.DOTALL,
)

# Matches a bare LaTeX command (not inside $ delimiters)
_BARE_LATEX_CMD_RE = re.compile(
    r'\\(?:'
    r'frac|sum|int|prod|partial|nabla|sqrt|'
    r'alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|'
    r'nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|'
    r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|'
    r'mathbb|mathcal|mathbf|mathrm|text|hat|bar|vec|tilde|overline|underline|'
    r'left|right|cdot|times|div|pm|mp|leq|geq|neq|approx|equiv|propto|'
    r'in|notin|subset|supset|cap|cup|rightarrow|leftarrow|Rightarrow|Leftarrow|'
    r'infty|forall|exists|lim|log|exp|ln|argmax|argmin|begin|end'
    r')\b'
)

# Matches any Unicode math character
_UNICODE_MATH_RE = re.compile(
    '[' + re.escape(''.join(_UNICODE_TO_LATEX.keys())) + ']'
)


def _has_math_content(text: str) -> bool:
    """Return True if *text* contains bare LaTeX commands or Unicode math chars."""
    return bool(_BARE_LATEX_CMD_RE.search(text) or _UNICODE_MATH_RE.search(text))


def _replace_unicode_math(text: str) -> str:
    """Replace all Unicode math characters with their LaTeX equivalents."""
    for uni_char, latex_cmd in _UNICODE_TO_LATEX.items():
        text = text.replace(uni_char, latex_cmd)
    return text


def _split_by_dollar_regions(text: str) -> list[tuple[str, str]]:
    """
    Split *text* into alternating ('delimited', ...) / ('bare', ...) segments
    based on existing $...$ and $$...$$ regions.
    """
    result: list[tuple[str, str]] = []
    last = 0
    for m in _DELIMITED_MATH_RE.finditer(text):
        if m.start() > last:
            result.append(('bare', text[last:m.start()]))
        result.append(('delimited', m.group(0)))
        last = m.end()
    if last < len(text):
        result.append(('bare', text[last:]))
    return result


def _is_math_token(token: str) -> bool:
    """
    Heuristic: return True if a whitespace-delimited token looks like part
    of a mathematical expression rather than ordinary prose.
    """
    if _BARE_LATEX_CMD_RE.search(token):          # e.g. \frac, \sum
        return True
    if re.search(r'[\^_\{\}]', token):            # sub/superscript or braces
        return True
    if re.search(r'[=\+\*\/\^_]', token) and not token.isalpha():
        return True                                # operators in a non-word token
    return False


def _is_standalone_math_expression(text: str) -> bool:
    """
    Return True when the stripped *text* is predominantly a math expression
    (≥ 70 % of whitespace-delimited tokens are math tokens) and therefore
    should be wrapped as display math  $$...$$  rather than inline  $...$ .
    """
    if not text or not _BARE_LATEX_CMD_RE.search(text):
        return False
    words = re.split(r'\s+', text.strip())
    words = [w for w in words if w]
    if not words:
        return False
    math_count = sum(1 for w in words if _is_math_token(w))
    ratio = math_count / len(words)
    return ratio >= 0.7 or (len(words) <= 4 and math_count >= 1)


def _wrap_inline_math_spans(text: str) -> str:
    """
    Walk *text* word-by-word (whitespace-delimited).  Consecutive math tokens
    are grouped and wrapped in  $...$ ;  prose tokens are left unchanged.
    """
    tokens = re.split(r'(\s+)', text)   # alternating: word | whitespace
    result: list[str] = []
    math_buf: list[str] = []

    def flush_math() -> None:
        if not math_buf:
            return
        buf = ''.join(math_buf)
        # Strip trailing whitespace out of the $ span
        core = buf.rstrip()
        tail = buf[len(core):]
        if core:
            result.append('$' + core + '$')
        if tail:
            result.append(tail)
        math_buf.clear()

    for tok in tokens:
        if not tok:
            continue
        if tok.strip() == '':               # pure whitespace
            if math_buf:
                math_buf.append(tok)        # buffer whitespace inside a span
            else:
                result.append(tok)
        elif _is_math_token(tok):
            math_buf.append(tok)
        else:
            flush_math()
            result.append(tok)

    flush_math()
    return ''.join(result)


def _fix_bare_math_segment(text: str) -> str:
    """
    Process a single bare (undelimited) text segment:
      1. Bail out early if no math content is present.
      2. Replace Unicode math chars with LaTeX equivalents.
      3. Wrap the result as  $$...$$ (standalone) or via inline span wrapping.
    """
    if not _has_math_content(text):
        return text

    converted = _replace_unicode_math(text)
    stripped  = converted.strip()

    if _is_standalone_math_expression(stripped):
        # Preserve any leading/trailing whitespace around the delimiters
        leading  = len(converted) - len(converted.lstrip())
        trailing = len(converted) - len(converted.rstrip())
        prefix   = converted[:leading]
        suffix   = converted[len(converted) - trailing:] if trailing else ''
        return prefix + '$$' + stripped + '$$' + suffix

    return _wrap_inline_math_spans(converted)


def normalize_equations(text: str) -> str:
    """
    Post-process LLM-generated text so that every mathematical expression
    is wrapped in LaTeX dollar-sign delimiters before being passed to
    ``text_to_flowables`` / matplotlib for rendering.

    Already-delimited regions ( $...$ and $$...$$ ) are left untouched.
    Everything else is inspected for bare LaTeX commands or Unicode math
    characters and wrapped appropriately.

    Parameters
    ----------
    text : str
        Raw text from the LLM (section content, derivations, summary, …).

    Returns
    -------
    str
        The same text with all math expressions properly delimited.
    """
    if not text:
        return text

    lines = text.split('\n')
    normalized: list[str] = []

    for line in lines:
        if not line.strip():
            normalized.append(line)
            continue

        segments = _split_by_dollar_regions(line)
        parts: list[str] = []
        for kind, content in segments:
            if kind == 'delimited':
                parts.append(content)   # already good
            else:
                parts.append(_fix_bare_math_segment(content))
        normalized.append(''.join(parts))

    return '\n'.join(normalized)

# ── End of equation normalizer ───────────────────────────────────────────────


def make_rl_image(latex_expr: str, max_width_pts: float = 400) -> RLImage | None:
    buf = latex_to_image(latex_expr)
    if buf is None:
        return None
    try:
        from PIL import Image as PILImage
        pil_img = PILImage.open(buf)
        w_px, h_px = pil_img.size
        dpi = 96
        w_pts = w_px * 72 / dpi
        h_pts = h_px * 72 / dpi
        scale = min(1.0, max_width_pts / w_pts)
        w_pts *= scale
        h_pts *= scale
        buf.seek(0)
        return RLImage(buf, width=w_pts, height=h_pts)
    except Exception as e:
        print(f"Image conversion failed: {e}")
        return None