"""
report_export.py
────────────────
PDF renderer for the EIS report.

Adapted from handbook_export.py (same idea: an FPDF subclass with small
semantic write helpers). Compared with the first version:

  - formulas are drawn as images (rendered LaTeX) with the LaTeX source in
    small grey text underneath;
  - inline math in sentences ($\\tau$, $R_{ct}$, $F/cm^2$) becomes real
    symbols, subscripts and superscripts;
  - figures are placed side by side (a "row") instead of one per page;
  - related blocks (a result heading + value + formula + assumptions) can be
    kept together on one page;
  - render_pdf(blocks) draws a whole report described by eis_report.py.

Expected location in the project:  src/export/report_export.py
Required fonts in <project root>/fonts/ :
    DejaVuSansCondensed.ttf, DejaVuSansCondensed-Bold.ttf, DejaVuSansMono.ttf
Requires fpdf2 >= 2.8 (sub/superscript support).
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from .latex_text import (
    FORMULA_DPI, png_size, render_formula_png, rich_segments,
)

# ─────────────────────────────────────────────────────────────────────────────
# Paths  (src/export/report_export.py -> parents[2] is the project root)
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_DIR     = PROJECT_ROOT / "fonts"
REPORT_DIR   = PROJECT_ROOT / "results" / "reports"

_VPOS = {"": "LINE", "sub": "SUB", "sup": "SUP"}     # our mode -> fpdf2 char_vpos
GREY = (110, 110, 110)


def _ensure_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def figure_to_png(fig, dpi: int = 200) -> bytes:
    """
    Render a matplotlib figure to PNG bytes (kept in memory, no temp file).
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    return buf.getvalue()


def safe_name(text: str) -> str:
    """Return a filesystem-safe slug (max 80 chars) derived from *text*."""
    slug = re.sub(r"[^\w\s-]", "", text.strip().lower())
    slug = re.sub(r"[\s-]+", "_", slug).strip("_")
    return slug[:80] or "eis_report"


# ─────────────────────────────────────────────────────────────────────────────
# The PDF class
# ─────────────────────────────────────────────────────────────────────────────

class ReportPDF(FPDF):
    """A4 report with a title footer and helpers to write content."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=15)

        # Fonts must be registered BEFORE the first page is added,
        # because footer() (called at the end of each page) uses them.
        self.add_font("DejaVu",     style="",  fname=str(FONT_DIR / "DejaVuSansCondensed.ttf"))
        self.add_font("DejaVu",     style="B", fname=str(FONT_DIR / "DejaVuSansCondensed-Bold.ttf"))
        self.add_font("DejaVuMono", style="",  fname=str(FONT_DIR / "DejaVuSansMono.ttf"))

        self.add_page()
        self.set_font("DejaVu", size=11)

    # ── Page furniture ────────────────────────────────────────────────────────

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", size=8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"{self.report_title}  -  page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    # ── Low-level text writing ────────────────────────────────────────────────

    def _put(self, text: str, height: float, size: float, bold: bool = False) -> None:
        """
        Write text WITHOUT ending the line. Inline math is converted by
        rich_segments() and each piece is written normal / subscript /
        superscript. write() wraps long text onto the next line by itself.
        """
        self.set_font("DejaVu", style="B" if bold else "", size=size)
        for segment, mode in rich_segments(text):
            self.char_vpos = _VPOS[mode]
            self.write(height, segment)
        self.char_vpos = "LINE"

    def _line(self, text: str, height: float = 6, size: float = 11,
              bold: bool = False, color=(0, 0, 0)) -> None:
        """Write one paragraph of rich text, then go to the next line."""
        self.set_text_color(*color)
        self._put(text, height, size, bold)
        self.ln(height)
        self.set_text_color(0, 0, 0)

    # ── Semantic write helpers ────────────────────────────────────────────────

    def write_h1(self, text: str) -> None:
        self._line(text, height=12, size=18, bold=True)
        self.ln(2)

    def write_h2(self, text: str) -> None:
        self.ln(4)
        self._line(text, height=10, size=14, bold=True)
        self.ln(1)

    def write_h3(self, text: str) -> None:
        self.ln(3)
        self._line(text, height=7, size=11.5, bold=True)

    def write_body(self, text: str) -> None:
        self._line(text, height=6, size=11)

    def write_note(self, text: str) -> None:
        """Small grey text: remarks, captions, labels."""
        self._line(text, height=5, size=9, color=GREY)

    def write_key_value(self, label: str, value: str) -> None:
        """One 'label: value' line, label in bold."""
        self._put(f"{label}:  ", 6, 11, bold=True)
        self._put(value, 6, 11)
        self.ln(6)

    def write_bullets(self, items: list[str]) -> None:
        """Bullet list with a hanging indent (wrapped lines align with the text)."""
        left = self.l_margin
        for item in items:
            self.set_x(left + 2)
            self.set_font("DejaVu", size=10)
            self.write(5.5, "•")
            self.set_left_margin(left + 7)       # wrapped lines start here
            self.set_x(left + 7)
            self._put(item, 5.5, 10)
            self.ln(5.5)
            self.set_left_margin(left)
        self.set_x(left)
        self.ln(1)

    def write_separator(self) -> None:
        self.ln(3)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    # ── Formulas ──────────────────────────────────────────────────────────────

    def write_formula(self, tex: str) -> None:
        """
        A display formula: the rendered image, centred, and the LaTeX source in
        small grey monospace underneath. If matplotlib cannot render the
        formula, only the source is shown.
        """
        png = render_formula_png(tex)
        if png is not None:
            wpx, hpx = png_size(png)
            w = wpx / FORMULA_DPI * 25.4                       # natural size, mm
            usable = self.w - self.l_margin - self.r_margin
            if w > usable:
                w = usable
            self.ln(1)
            # No y given -> fpdf2 starts a new page by itself if it does not fit
            self.image(io.BytesIO(png), x=(self.w - w) / 2, w=w)
            self.ln(1)

        self.set_font("DejaVuMono", size=7.5)
        self.set_text_color(*GREY)
        self.multi_cell(0, 4, f"LaTeX:  {tex}", align="C",
                        new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font("DejaVu", size=11)
        self.ln(2)

    # ── Figures ───────────────────────────────────────────────────────────────

    def add_figure_row(self, items, heading: str | None = None,
                       max_height: float = 95, gap: float = 6) -> None:
        """
        Place 1-3 figures side by side.

        items      : list of (caption, png_bytes)
        heading    : optional section title, kept on the same page as the row
        max_height : tall figures (Bode) are shrunk to at most this many mm
        """
        n = len(items)
        usable = self.w - self.l_margin - self.r_margin
        col_w = (usable - gap * (n - 1)) / n

        # Final size of each image: column width, but not taller than max_height
        sizes = []
        for _, png in items:
            wpx, hpx = png_size(png)
            w, h = col_w, col_w * hpx / wpx
            if h > max_height:
                w, h = w * max_height / h, max_height
            sizes.append((w, h))

        caption_space = 12
        row_h = max(h for _, h in sizes) + caption_space
        needed = row_h + (14 if heading else 0)

        # Not enough room left on this page -> start a new one
        if self.get_y() + needed > self.page_break_trigger:
            self.add_page()
        if heading:
            self.write_h2(heading)

        y0 = self.get_y()
        for k, ((caption, png), (w, h)) in enumerate(zip(items, sizes)):
            col_x = self.l_margin + k * (col_w + gap)
            self.image(io.BytesIO(png), x=col_x + (col_w - w) / 2, y=y0, w=w)
            self.set_xy(col_x, y0 + h + 1)
            self.set_font("DejaVu", size=8.5)
            self.set_text_color(*GREY)
            self.multi_cell(col_w, 4.5, caption, align="C",
                            new_x="LEFT", new_y="TOP")
        self.set_text_color(0, 0, 0)
        self.set_font("DejaVu", size=11)
        self.set_xy(self.l_margin, y0 + row_h)


# ─────────────────────────────────────────────────────────────────────────────
# Draw a whole report from blocks (see eis_report.py for the block kinds)
# ─────────────────────────────────────────────────────────────────────────────

def _draw(pdf: ReportPDF, blocks: list) -> None:
    for block in blocks:
        kind = block[0]
        if kind == "title":
            pdf.write_h1(block[1])
        elif kind == "h2":
            pdf.write_h2(block[1])
        elif kind == "h3":
            pdf.write_h3(block[1])
        elif kind == "text":
            pdf.write_body(block[1])
        elif kind == "note":
            pdf.write_note(block[1])
        elif kind == "kv":
            pdf.write_key_value(block[1], block[2])
        elif kind == "bullets":
            pdf.write_bullets(block[1])
        elif kind == "formula":
            pdf.write_formula(block[1])
        elif kind == "figures":
            heading = block[2] if len(block) > 2 else None
            pdf.add_figure_row(block[1], heading=heading)
        elif kind == "separator":
            pdf.write_separator()
        elif kind == "group":
            # unbreakable(): if the group does not fit in what is left of the
            # page, the whole group moves to the next page
            with pdf.unbreakable():
                _draw(pdf, block[1])
        else:
            raise ValueError(f"Unknown block kind: {kind!r}")


def render_pdf(blocks: list, title: str = "EIS analysis report") -> ReportPDF:
    """Draw the blocks and return the (not yet saved) PDF."""
    pdf = ReportPDF(title)
    _draw(pdf, blocks)
    return pdf


def save_report(pdf: ReportPDF, name_hint: str) -> str:
    """Write the PDF to results/reports/<name>_<timestamp>.pdf, return its path."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"{safe_name(name_hint)}_{timestamp}.pdf"
    pdf.output(str(path))
    return str(path)
