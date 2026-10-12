"""
latex_text.py
─────────────
Math helpers shared by the PDF and the Word export.

A PDF/Word library cannot read LaTeX, so the report uses two different tricks:

  1. DISPLAY formulas (the big centred ones)  -> rendered to a PNG image with
     matplotlib's math engine ("mathtext"): render_formula_png().
  2. INLINE math inside sentences ($\\tau$, $R_{ct}$, $F/cm^2$) -> converted to
     plain text pieces tagged normal / subscript / superscript:
     rich_segments(). Each exporter then writes the pieces with its own
     sub/superscript feature.

Only the small subset of LaTeX that this project uses is supported
(Greek letters, subscripts, superscripts, \\frac, \\,, \\approx ...). An unknown
command is shown as its bare name instead of crashing.

Expected location: src/export/latex_text.py
"""

from __future__ import annotations

import io
import re

import matplotlib
from matplotlib.figure import Figure

# ─────────────────────────────────────────────────────────────────────────────
# 1. Display formulas -> PNG
# ─────────────────────────────────────────────────────────────────────────────

FORMULA_DPI = 300   # resolution of the formula images (also used to size them)


def render_formula_png(tex: str, fontsize: int = 13) -> bytes | None:
    """
    Render LaTeX math to a transparent PNG (bytes). Returns None if matplotlib
    cannot parse the formula, so the caller can fall back to the source text.

    A bare Figure() is used instead of pyplot, so we never disturb the figures
    that Streamlit is displaying.
    """
    try:
        # "cm" = Computer Modern, the font of real LaTeX documents
        with matplotlib.rc_context({"mathtext.fontset": "cm"}):
            fig = Figure(figsize=(0.01, 0.01))
            fig.text(0, 0, f"${tex}$", fontsize=fontsize)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=FORMULA_DPI,
                        bbox_inches="tight", pad_inches=0.04, transparent=True)
        return buf.getvalue()
    except Exception:
        return None


def png_size(png: bytes) -> tuple[int, int]:
    """(width, height) of a PNG in pixels."""
    from PIL import Image          # Pillow is already installed with matplotlib
    with Image.open(io.BytesIO(png)) as im:
        return im.size


# ─────────────────────────────────────────────────────────────────────────────
# 2. Inline math -> [(text, mode)]   mode is "" (normal), "sub" or "sup"
# ─────────────────────────────────────────────────────────────────────────────

SYMBOLS = {
    # greek
    r"\tau": "τ", r"\mu": "µ", r"\pi": "π", r"\kappa": "κ", r"\sigma": "σ",
    r"\chi": "χ", r"\omega": "ω", r"\Omega": "Ω", r"\Delta": "Δ", r"\alpha": "α",
    r"\beta": "β", r"\phi": "φ", r"\varphi": "φ", r"\theta": "θ", r"\lambda": "λ",
    r"\rho": "ρ", r"\epsilon": "ε", r"\eta": "η",
    # operators and relations
    r"\approx": "≈", r"\times": "×", r"\cdot": "·", r"\pm": "±",
    r"\parallel": "‖", r"\le": "≤", r"\ge": "≥", r"\rightarrow": "→",
    r"\infty": "∞", r"\circ": "°",
    # spacing
    r"\,": "\u2009", r"\;": " ", r"\:": " ", r"\ ": " ", r"\!": "",
    r"\quad": "  ", r"\qquad": "    ",
    # sizing commands that mean nothing in plain text
    r"\left": "", r"\right": "",
}
_TEXT_COMMANDS = {r"\mathrm", r"\text", r"\mathit", r"\mathbf"}   # keep their argument

_COMMAND = re.compile(r"\\([A-Za-z]+|.)")


def _read_arg(s: str, i: int) -> tuple[str, int]:
    """
    Read one LaTeX argument starting at s[i]: either a {...} group (nested
    braces allowed) or a single character / command. Returns (content, next_i).
    """
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        depth = 0
        for j in range(i, len(s)):
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
        return s[i + 1:], len(s)             # unbalanced: take the rest
    if s[i] == "\\":
        m = _COMMAND.match(s, i)
        return m.group(0), m.end()
    return s[i], i + 1


def latex_to_segments(tex: str, mode: str = "") -> list[tuple[str, str]]:
    """Convert a LaTeX fragment (without the $ signs) to [(text, mode), ...]."""
    segs: list[tuple[str, str]] = []
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            segs.append((buf, mode))
            buf = ""

    i = 0
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            m = _COMMAND.match(tex, i)
            cmd = m.group(0)
            i = m.end()
            if cmd == r"\frac":                          # a/b  (inline form)
                num, i = _read_arg(tex, i)
                den, i = _read_arg(tex, i)
                flush()
                for part, sep in ((num, "/"), (den, "")):
                    inner = latex_to_segments(part, mode)
                    plain = "".join(t for t, _ in inner)
                    if len(plain) > 1:                   # (a+b)/c needs brackets
                        segs.append(("(", mode)); segs += inner; segs.append((")", mode))
                    else:
                        segs += inner
                    if sep:
                        segs.append((sep, mode))
            elif cmd in _TEXT_COMMANDS:
                arg, i = _read_arg(tex, i)
                flush()
                segs += latex_to_segments(arg, mode)
            elif cmd in SYMBOLS:
                buf += SYMBOLS[cmd]
            else:                                        # unknown: show its name
                buf += cmd[1:]
        elif c in "_^":
            flush()
            arg, i = _read_arg(tex, i + 1)
            segs += latex_to_segments(arg, "sub" if c == "_" else "sup")
        elif c in "{}":
            i += 1                                       # grouping braces: skip
        else:
            buf += c
            i += 1
    flush()
    return segs


_MATH = re.compile(r"\$(.+?)\$")


def rich_segments(text: str) -> list[tuple[str, str]]:
    """
    Split ordinary text containing $...$ inline math into [(text, mode), ...].

        "Time constant $\\tau$"  ->  [("Time constant ", ""), ("τ", "")]
        "$R_{ct}$ in $F/cm^2$"   ->  [("R",""),("ct","sub")," in ", ("F/cm",""),("2","sup")]
    """
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _MATH.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], ""))
        out += latex_to_segments(m.group(1))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], ""))

    merged: list[tuple[str, str]] = []                   # join neighbours of same mode
    for t, mode in out:
        if merged and merged[-1][1] == mode:
            merged[-1] = (merged[-1][0] + t, mode)
        else:
            merged.append((t, mode))
    return merged


def plain_text(text: str) -> str:
    """Text with all math converted but no sub/superscript formatting."""
    return "".join(t for t, _ in rich_segments(text))
