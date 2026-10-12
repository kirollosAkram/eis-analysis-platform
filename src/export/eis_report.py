"""
eis_report.py
─────────────
Decide WHAT goes in the EIS report. It does not draw anything.

The result is a list of "blocks": plain tuples describing the content. The same
list is drawn as PDF by report_export.render_pdf() and as Word by
report_docx.render_docx(), so the report is written only once.

Block kinds
-----------
    ("title",   text)                   main title
    ("h2",      text)                   section heading
    ("h3",      text)                   sub-heading
    ("text",    text)                   normal paragraph
    ("note",    text)                   small grey text
    ("kv",      label, value)           "label: value" line, label in bold
    ("bullets", [text, ...])            bullet list
    ("formula", latex)                  display formula (rendered + LaTeX source)
    ("figures", [(caption, png)], heading)   figures side by side
    ("separator",)                      horizontal line
    ("group",   [block, ...])           blocks to keep together on one page

Any text may contain inline math between $...$, e.g. "Time constant $\\tau$".

The report mirrors the three levels used everywhere in the project:
    1. electrical parameters   (fit of the equivalent circuit)
    2. measurable EIS features (read from the data, no model)
    3. interpretation          (derived quantities + their assumptions)

Every number comes from the existing modules (fit_model, rmse_complex,
chi_square, extract_features, interpret_randles); nothing is computed here.

Expected location: src/export/eis_report.py
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime


def _num(x: float) -> str:
    """
    Format a number; scientific notation becomes proper LaTeX:
        9.994e-06  ->  $9.994 \\times 10^{-6}$
    """
    s = f"{x:.4g}"
    if "e" in s:
        mantissa, exponent = s.split("e")
        return f"${mantissa} \\times 10^{{{int(exponent)}}}$"
    return s


# ─────────────────────────────────────────────────────────────────────────────
# One small function per section, so each part can be read (and changed) alone
# ─────────────────────────────────────────────────────────────────────────────

def _section_fit(param_labels, popt, rmse, chi2) -> list:
    blocks = [
        ("h2", "1. Equivalent-circuit fit"),
        ("note", "Electrical parameters of the chosen model, found by "
                 "least-squares fitting. They describe the circuit, not yet "
                 "the chemistry."),
    ]
    for i, value in enumerate(popt):
        # param_labels = [("R_s", "Ω"), ...]; fall back to p1, p2... if missing
        if param_labels and i < len(param_labels):
            label, unit = param_labels[i]
        else:
            label, unit = f"p{i + 1}", ""
        blocks.append(("kv", f"${label}$", f"{_num(value)} {unit}".strip()))

    blocks.append(("kv", "RMSE (complex)", f"{_num(rmse)} Ω"))
    blocks.append(("kv", "χ² (σ = 1)", _num(chi2)))
    return blocks


def _section_features(feat) -> list:
    blocks = [
        ("h2", "2. Measured EIS features (no model)"),
        ("note", "Read directly from the data. If the system behaves like a "
                 "Randles circuit: $R_{high} \\approx R_s$, "
                 "$R_{low} - R_{high} \\approx R_{ct}$, and $f_{apex}$ is "
                 "related to $R_{ct}$ and $C_{dl}$ as below."),
        ("kv", "$R_{high}$", f"{_num(feat.R_high)} Ω"),
        ("kv", "$R_{low}$", f"{_num(feat.R_low)} Ω"),
        ("kv", "$R_{low} - R_{high}$", f"{_num(feat.R_diff)} Ω"),
        ("kv", "$f_{apex}$", f"{_num(feat.f_apex)} Hz"),
        ("formula", r"f_{apex} = \frac{1}{2 \pi \, R_{ct} \, C_{dl}}"),
    ]

    # Same reliability warnings the app shows: a report must not hide them.
    warnings = []
    if not feat.R_high_reliable:
        warnings.append("High-frequency end does not reach the real axis: "
                        "$R_{high}$ is only an upper bound for $R_s$.")
    if not feat.R_low_reliable:
        warnings.append("No low-frequency plateau on the real axis: "
                        "$R_{low}$ is not an $R_s + R_{ct}$ estimate.")
    if not feat.apex_resolved:
        warnings.append("The maximum of $-Z''$ is at the edge of the measured "
                        "range: $f_{apex}$ is not resolved.")
    if warnings:
        blocks += [("h3", "Reliability warnings"), ("bullets", warnings)]
    return blocks


def _section_interpretation(results, inputs, check) -> list:
    blocks = [
        ("h2", "3. Electrochemical interpretation"),
        ("note", "Derived quantities. Each one is valid only under the "
                 "assumptions listed with it."),
    ]

    if inputs:
        blocks += [("h3", "Inputs provided"),
                   ("bullets", [f"{k}: {v}" for k, v in inputs.items()])]

    # An assumption used by 2+ results (e.g. "the circuit is a Randles circuit")
    # is written once and numbered A1, A2...; each result then only points to it.
    # Not every result relies on every shared assumption (conductivity, for
    # instance, does not need the Randles one), hence "points to" and not "all".
    counts = Counter(a for r in results for a in r.assumptions)
    shared = [a for a, c in counts.items() if c >= 2]
    shared_id = {a: f"A{i + 1}" for i, a in enumerate(shared)}
    if shared:
        blocks += [("h3", "Shared assumptions"),
                   ("bullets", [f"{shared_id[a]}: {a}" for a in shared])]

    for r in results:                                   # r is an InterpretedResult
        own = [a for a in r.assumptions if a not in shared_id]
        used = [shared_id[a] for a in r.assumptions if a in shared_id]
        group = [
            ("h3", r.name),
            ("kv", "Value", f"{_num(r.value)} {r.unit}"),
            ("formula", r.formula),
        ]
        if used:
            group.append(("note", "Relies on shared assumption(s): "
                                  + ", ".join(used)))
        if own:
            group += [("note", "Additional assumptions:"), ("bullets", own)]
        if r.notes:
            group += [("note", "Notes:"), ("bullets", r.notes)]
        blocks.append(("group", group))                 # kept on one page

    # Fit-vs-data cross-check (ConsistencyCheck from interpretation.py)
    if check is not None:
        if check.consistent:
            verdict = ("The fit and the data agree on the time constant. This "
                       "supports the single-semicircle model but does not "
                       "prove it.")
        else:
            verdict = ("The fitted $f_c$ and the measured $f_{apex}$ disagree: "
                       "treat $\\tau$, $j_0$ and $C_{dl}/A$ with caution "
                       "(possible CPE behaviour, overlapping time constants, "
                       "diffusion tail, poor fit or coarse frequency spacing).")
        blocks.append(("group", [
            ("h3", "Consistency check: fit vs data"),
            ("kv", "$f_c$ (fit)", f"{_num(check.f_c)} Hz"),
            ("kv", "$f_{apex}$ (data)", f"{_num(check.f_apex)} Hz"),
            ("kv", "Difference", f"{100 * check.rel_diff:.1f} %"),
            ("text", verdict),
        ]))
    return blocks


def _section_figures(figures) -> list:
    """Figures two per row; the heading stays with the first row."""
    blocks = []
    for i in range(0, len(figures), 2):
        row = list(figures[i:i + 2])
        blocks.append(("figures", row, "4. Figures" if i == 0 else None))
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Public function
# ─────────────────────────────────────────────────────────────────────────────

def build_eis_report_blocks(
    model_name: str,
    popt,
    rmse: float,
    chi2: float,
    param_labels: list | None = None,
    feat=None,
    results: list | None = None,
    inputs: dict | None = None,
    check=None,
    figures: list | None = None,
    data_name: str = "",
) -> list:
    """
    Return the report as a list of blocks (see the module docstring).

    Parameters
    ----------
    model_name   : e.g. "Randles (Rs + Rct‖Cdl)"
    popt, rmse, chi2 : fit output and metrics
    param_labels : [(label, unit), ...] in the same order as popt;
                   labels are LaTeX without the $ signs, e.g. ("R_s", "Ω")
    feat         : features object from extract_features (optional)
    results      : list of InterpretedResult from interpret_randles (optional)
    inputs       : dict {"Electrode area": "0.07 cm²", ...} (optional)
    check        : ConsistencyCheck from compare_fc_fapex (optional)
    figures      : list of (caption, PNG bytes)
    data_name    : name of the uploaded file, shown under the title

    Optional sections are skipped when their input is None / empty.
    """
    blocks = [("title", "EIS analysis report"),
              ("text", f"Model: {model_name}")]
    if data_name:
        blocks.append(("text", f"Data file: {data_name}"))
    blocks += [("note", f"Generated on {datetime.now():%Y-%m-%d %H:%M}"),
               ("separator",)]

    blocks += _section_fit(param_labels, popt, rmse, chi2)
    if feat is not None:
        blocks += _section_features(feat)
    if results:
        blocks += _section_interpretation(results, inputs, check)
    if figures:
        blocks += _section_figures(figures)
    return blocks
