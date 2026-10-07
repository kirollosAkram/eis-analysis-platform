"""
interpretation.py — Turn fitted equivalent-circuit parameters into
electrochemical quantities, each labelled with its assumptions.

Three levels are kept separate on purpose:
  1. Electrical parameters   : Rs, Rct, Cdl   (from fit_model, in ohm / farad)
  2. Derived quantities      : tau, f_c, j0, Cdl/A, conductivity
  3. Physical interpretation : only valid under the assumptions listed
                               with each result.

Units used in this module
-------------------------
  resistance  : ohm
  capacitance : farad
  area        : cm^2   (electrode area, or cell cross-section)
  length      : cm
  temperature : kelvin
"""

from dataclasses import dataclass, field
import numpy as np

# Physical constants (CODATA)
R_GAS = 8.314462618      # J / (mol K)
F_FARADAY = 96485.33212  # C / mol


# ---------------------------------------------------------------------
# Part A: plain math functions (no labels, easy to test)
# ---------------------------------------------------------------------

def _check_positive(**kwargs):
    """Raise a clear error if any value is not strictly positive."""
    for name, value in kwargs.items():
        if value is None or not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive number, got {value!r}")


def time_constant(Rct: float, Cdl: float) -> float:
    """tau = Rct * Cdl  [seconds]"""
    _check_positive(Rct=Rct, Cdl=Cdl)
    return Rct * Cdl


def characteristic_frequency(Rct: float, Cdl: float) -> float:
    """f_c = 1 / (2 pi tau)  [Hz] -- the top of the Nyquist semicircle."""
    return 1.0 / (2.0 * np.pi * time_constant(Rct, Cdl))


def exchange_current_density(Rct: float, area_cm2: float, n: int,
                             T_kelvin: float = 298.15) -> float:
    """
    j0 = R T / (n F Rct A)   [A / cm^2]

    Rct * A has units ohm*cm^2 (area-specific resistance), so dividing
    R T / (n F) [volts] by it gives A/cm^2.
    """
    _check_positive(Rct=Rct, area_cm2=area_cm2, n=n, T_kelvin=T_kelvin)
    return (R_GAS * T_kelvin) / (n * F_FARADAY * Rct * area_cm2)


def specific_capacitance(Cdl: float, area_cm2: float) -> float:
    """Cdl / A  [F / cm^2]"""
    _check_positive(Cdl=Cdl, area_cm2=area_cm2)
    return Cdl / area_cm2


def cell_constant_parallel_plate(length_cm: float, area_cm2: float) -> float:
    """K = L / A  [1 / cm] for a uniform column of electrolyte."""
    _check_positive(length_cm=length_cm, area_cm2=area_cm2)
    return length_cm / area_cm2


def electrolyte_conductivity(Rs: float, cell_constant_per_cm: float) -> float:
    """kappa = K / Rs  [S / cm]   (K = L/A, the cell constant)"""
    _check_positive(Rs=Rs, cell_constant_per_cm=cell_constant_per_cm)
    return cell_constant_per_cm / Rs


# ---------------------------------------------------------------------
# Part B: labelled results
# ---------------------------------------------------------------------

@dataclass
class InterpretedResult:
    """One derived quantity together with the context needed to trust it."""
    name: str
    value: float
    unit: str
    formula: str
    assumptions: list = field(default_factory=list)  # always valid caveats
    notes: list = field(default_factory=list)        # data-dependent remarks


# Assumptions shared by everything that uses a Randles-type fit.
_RANDLES_ASSUMPTION = (
    "The fitted circuit is Rs + (Rct || Cdl): one semicircle, and Cdl is "
    "an ideal capacitor (no CPE / non-ideal behaviour)."
)


def interpret_randles(Rs: float, Rct: float, Cdl: float,
                      area_cm2: float = None,
                      n: int = None,
                      T_kelvin: float = 298.15,
                      cell_constant_per_cm: float = None) -> list:
    """
    Compute every quantity that the provided inputs allow.

    Always computed : tau, f_c           (need only Rct, Cdl)
    Needs area      : specific Cdl
    Needs area + n  : j0
    Needs cell const: electrolyte conductivity

    Returns a list of InterpretedResult. Quantities whose inputs are
    missing are simply left out (never guessed).
    """
    results = []

    # ---- 1. Time constant and characteristic frequency ----------------
    tau = time_constant(Rct, Cdl)
    results.append(InterpretedResult(
        name="Time constant tau",
        value=tau, unit="s",
        formula="$\tau$ $= R_{ct} * C_{dl}$",
        assumptions=[_RANDLES_ASSUMPTION],
        notes=["Describes how fast the interface charges/discharges. "
               "It is a property of the fit, not yet a chemical statement."],
    ))

    results.append(InterpretedResult(
        name="Characteristic frequency $f_c$",
        value=1.0 / (2 * np.pi * tau), unit="Hz",
        formula="$f_c$ $= 1 / (2 \pi \tau)$",
        assumptions=[_RANDLES_ASSUMPTION],
        notes=["Should match the apex frequency measured directly from the "
               "Nyquist plot (f_apex); a large mismatch means the "
               "single-semicircle model does not describe the data well."],
    ))

    # ---- 2. Specific double-layer capacitance -------------------------
    if area_cm2 is not None:
        c_spec = specific_capacitance(Cdl, area_cm2)
        c_uf = c_spec * 1e6
        notes = []
        # Rule of thumb only: smooth metal electrodes in aqueous electrolyte
        # are often quoted around 10-50 uF/cm^2. Very different values are a
        # hint, not a proof, that something is off.
        if c_uf < 5 or c_uf > 100:
            notes.append(
                f"{c_uf:.3g} uF/cm^2 is outside the usual ~5-100 uF/cm^2 "
                "range for flat electrodes in aqueous electrolyte. Possible "
                "reasons: real area differs from the area you entered "
                "(roughness, porosity), a surface film or functionalised "
                "layer, a non-aqueous electrolyte, or a non-ideal (CPE) "
                "interface. EIS alone cannot tell which."
            )
        results.append(InterpretedResult(
            name="Specific double-layer capacitance",
            value=c_spec, unit="$F/cm^2$",
            formula="$C_{spec} = C_{dl} / A$",
            assumptions=[
                _RANDLES_ASSUMPTION,
                "A is the true electroactive area, not just the geometric area.",
                "The fitted capacitance is really the double layer (not "
                "adsorption pseudocapacitance or a coating).",
            ],
            notes=notes,
        ))

    # ---- 3. Exchange current density ----------------------------------
    if area_cm2 is not None and n is not None:
        j0 = exchange_current_density(Rct, area_cm2, n, T_kelvin)
        results.append(InterpretedResult(
            name="Exchange current density $j_0$",
            value=j0, unit="$A/cm^2$",
            formula="$j_0$ $= R T / (n F _{ct} A)$",
            assumptions=[
                _RANDLES_ASSUMPTION,
                "Measured at equilibrium (open-circuit) with both the "
                "oxidised and reduced species present, small AC amplitude "
                "(linearised Butler-Volmer).",
                "Rct is purely the charge-transfer resistance: no diffusion "
                "(Warburg) or film resistance mixed into it.",
                "Single, simple electron-transfer reaction; n is the number "
                "of electrons of that reaction (ambiguous for multi-step "
                "mechanisms).",
                "A is the true electroactive area.",
                f"T = {T_kelvin:.2f} K.",
            ],
            notes=["If Rct also contains other resistive contributions, "
                   "j0 is underestimated."],
        ))

    # ---- 4. Electrolyte conductivity ----------------------------------
    if cell_constant_per_cm is not None:
        kappa = electrolyte_conductivity(Rs, cell_constant_per_cm)
        results.append(InterpretedResult(
            name="Electrolyte conductivity",
            value=kappa, unit="$S/cm$",
            formula="$\kappa$ $= K / Rs,  K = L / A$ (cell constant)",
            assumptions=[
                "Rs is entirely electrolyte resistance (wires, contacts and "
                "reference-electrode junction add to it).",
                "Uniform current distribution between electrodes, so that "
                "the cell constant K = L/A is valid.",
                "Rs is read at high frequency, where the cell is purely "
                "resistive.",
            ],
            notes=["1 S/cm = 1000 mS/cm. Compare to a calibrated standard "
                   "solution to validate the cell constant."],
        ))

    return results
