"""
rc_circuit.py — Simulation of series RC circuit impedance

Z_RC = R + 1 / (j * omega * C)
"""

import numpy as np

def simulate_rc_series(R: float, C: float, frequencies: np.ndarray, noise_level: float = 0.0):
    """
    Simulate impedance of a series RC circuit.

    Parameters
    ----------
    R : float
        Resistance in ohms.
    C : float
        Capacitance in farads.
    frequencies : np.ndarray
        Frequency array in Hz.
    noise_level : float
        Standard deviation of Gaussian noise added to both real and imag parts.

    Returns
    -------
    Z : np.ndarray
        Complex impedance array.
    """
    omega = 2 * np.pi * frequencies
    Z_R = R
    Z_C = 1 / (1j * omega * C)
    Z = Z_R + Z_C

    if noise_level > 0:
        noise_real = np.random.normal(0, noise_level, size=len(frequencies))
        noise_imag = np.random.normal(0, noise_level, size=len(frequencies))
        Z = (Z.real + noise_real) + 1j * (Z.imag + noise_imag)

    return Z