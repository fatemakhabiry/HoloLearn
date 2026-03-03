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