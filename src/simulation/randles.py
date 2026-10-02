"""
randles.py — Simulation of a simplified Randles circuit

Circuit:  Rs in series with (Rct in parallel with Cdl)

    Z = Rs + 1 / (1/Rct + j * omega * Cdl)

Physical picture (a MODEL, valid only if the interface behaves like this):
    Rs  : electrolyte / contact resistance
    Rct : charge-transfer resistance of the electrode reaction
    Cdl : double-layer capacitance at the electrode/electrolyte interface
"""

import numpy as np


def simulate_randles(Rs: float, Rct: float, Cdl: float,
                     frequencies: np.ndarray, noise_level: float = 0.0):
    """
    Simulate impedance of a simplified Randles circuit.

    Parameters
    ----------
    Rs : float
        Series (solution) resistance in ohms.
    Rct : float
        Charge-transfer resistance in ohms.
    Cdl : float
        Double-layer capacitance in farads.
    frequencies : np.ndarray
        Frequency array in Hz.
    noise_level : float
        Standard deviation (in ohms) of Gaussian noise added to both
        the real and imaginary parts (same convention as rc_circuit.py).

    Returns
    -------
    Z : np.ndarray
        Complex impedance array.
    """
    omega = 2 * np.pi * frequencies

    # Rct and Cdl are in parallel, so their ADMITTANCES (1/Z) add up
    Y_parallel = 1 / Rct + 1j * omega * Cdl
    Z_parallel = 1 / Y_parallel

    # Rs is in series, so its impedance simply adds
    Z = Rs + Z_parallel

    if noise_level > 0:
        noise_real = np.random.normal(0, noise_level, size=len(frequencies))
        noise_imag = np.random.normal(0, noise_level, size=len(frequencies))
        Z = (Z.real + noise_real) + 1j * (Z.imag + noise_imag)

    return Z
