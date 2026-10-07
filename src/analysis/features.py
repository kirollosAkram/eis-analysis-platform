"""
features.py — Model-free feature extraction from impedance data

These features are read DIRECTLY from the measured spectrum. No equivalent
circuit and no fit are involved, so they can be used to:
  1. get good initial guesses for the fit, and
  2. cross-check the fit afterwards.

Convention (same as the rest of the project):
  Z = real + 1j * imag, with imag NEGATIVE for capacitive behaviour.
  Nyquist plots show Z' on x and -Z'' on y.

What each feature is (measurable) vs. what it MIGHT mean (interpretation):
  R_high  -> real-axis value at high frequency
             If the system looks like a Randles circuit: ~ Rs (series/electrolyte resistance)
  R_low   -> real-axis value at low frequency
             If the system looks like a Randles circuit: ~ Rs + Rct
  f_apex  -> frequency where -Z'' is maximal (top of the semicircle)
             If the semicircle is ideal: f_apex = 1 / (2*pi*Rct*Cdl)
The "if" parts are assumptions about the system, not facts read from the data.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class EISFeatures:
    """Container for the three model-free features and their reliability flags."""

    R_high: float              # Z' at the high-frequency end (ohm)
    R_high_reliable: bool      # True if the data actually reach the real axis there

    R_low: float               # Z' at the low-frequency end (ohm)
    R_low_reliable: bool       # True if the data have flattened onto the real axis there

    f_apex: float              # frequency of the maximum of -Z'' (Hz)
    apex_resolved: bool        # True if the maximum is inside the data, not at an edge
    neg_Zimag_apex: float      # height of the apex, max(-Z'') (ohm)

    @property
    def R_diff(self) -> float:
        """R_low - R_high. For a Randles-like spectrum this is ~ Rct."""
        return self.R_low - self.R_high


def _edge_value(frequencies, real, imag, at_high_freq, edge_points, tol, ref):
    """
    Estimate Z' where the spectrum meets the real axis (Z'' = 0) at one end.

    Strategy:
      1. Look only at the last `edge_points` points of that end.
      2. If Z'' changes sign there, interpolate linearly to the crossing.
      3. Otherwise take Z' of the outermost point.
    The value is flagged 'reliable' if we found a crossing OR the outermost
    point is already very close to the real axis (|Z''| < tol * ref).
    """
    n = len(frequencies)
    k = min(edge_points, n)

    # Frequencies are sorted ascending: high-frequency end = last rows
    idx = np.arange(n - k, n) if at_high_freq else np.arange(0, k)

    # Search sign changes of imag between neighbouring points in that window
    crossings = [i for i in idx[:-1] if imag[i] * imag[i + 1] < 0]

    if crossings:
        # Take the crossing closest to the outermost point
        i = crossings[-1] if at_high_freq else crossings[0]
        # Linear interpolation: fraction t where imag goes through 0
        t = imag[i] / (imag[i] - imag[i + 1])
        return real[i] + t * (real[i + 1] - real[i]), True

    outer = n - 1 if at_high_freq else 0
    reliable = abs(imag[outer]) < tol * ref
    return real[outer], reliable


def _find_apex(frequencies, neg_imag):
    """
    Find the frequency where -Z'' is maximal.

    The raw maximum is limited to the measured frequencies, so we refine it
    with a parabola through the maximum point and its two neighbours, fitted
    in log10(f) (impedance spectra are spread logarithmically in frequency).
    """
    n = len(frequencies)
    k = int(np.argmax(neg_imag))

    # Maximum at the edge -> the top of the semicircle was not measured
    if k == 0 or k == n - 1:
        return float(frequencies[k]), False, float(neg_imag[k])

    x = np.log10(frequencies[k - 1:k + 2])
    y = neg_imag[k - 1:k + 2]

    denom = y[0] - 2 * y[1] + y[2]       # curvature of the parabola (<= 0 at a peak)
    if denom >= 0:                        # flat top: no refinement possible
        return float(frequencies[k]), True, float(y[1])

    # Vertex of the parabola, in units of "grid steps" away from the centre point
    offset = 0.5 * (y[0] - y[2]) / denom
    offset = float(np.clip(offset, -1.0, 1.0))
    step = (x[2] - x[0]) / 2             # average spacing in log10(f)
    x_apex = x[1] + offset * step

    # Height of the parabola at its vertex
    y_apex = y[1] - 0.25 * (y[0] - y[2]) * offset

    return float(10 ** x_apex), True, float(y_apex)


def extract_features(frequencies: np.ndarray,
                     Z_data: np.ndarray,
                     edge_points: int = 5,
                     tol: float = 0.05) -> EISFeatures:
    """
    Extract R_high, R_low and f_apex directly from the data.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency vector (Hz). Same input as fit_model().
    Z_data : np.ndarray
        Complex impedance (real + 1j*imag, imag negative for capacitive).
    edge_points : int
        How many points at each end are searched for a real-axis crossing.
    tol : float
        An end counts as 'on the real axis' if |Z''| < tol * max|Z''|.

    Returns
    -------
    EISFeatures
    """
    frequencies = np.asarray(frequencies, dtype=float)
    Z_data = np.asarray(Z_data, dtype=complex)

    if len(frequencies) < 3:
        raise ValueError("Need at least 3 points to extract features.")

    # Sort by frequency (ascending), in case the input is not sorted
    order = np.argsort(frequencies)
    f = frequencies[order]
    real = Z_data.real[order]
    imag = Z_data.imag[order]

    ref = np.max(np.abs(imag))  # size scale of the spectrum, used for tolerances
    if ref == 0:
        raise ValueError("Imaginary part is zero everywhere: nothing to extract.")

    R_high, R_high_ok = _edge_value(f, real, imag, True, edge_points, tol, ref)
    R_low, R_low_ok = _edge_value(f, real, imag, False, edge_points, tol, ref)
    f_apex, apex_ok, height = _find_apex(f, -imag)

    return EISFeatures(
        R_high=float(R_high), R_high_reliable=R_high_ok,
        R_low=float(R_low), R_low_reliable=R_low_ok,
        f_apex=f_apex, apex_resolved=apex_ok, neg_Zimag_apex=height,
    )