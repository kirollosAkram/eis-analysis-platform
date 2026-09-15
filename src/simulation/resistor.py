"""
resistor.py — Simulation of ideal resistor impedance

Z_R = R
"""

import numpy as np

def simulate_resistor(R: float, frequencies: np.ndarray, noise_level: float = 0.0):
    """
    Simulate impedance of an ideal resistor.

    Parameters
    ----------
    R : float
        Resistance in ohms.
    frequencies : np.ndarray
        Frequency array in Hz.
    noise_level : float
        Standard deviation of Gaussian noise added to real(Z).

    Returns
    -------
    Z : np.ndarray
        Complex impedance array.
    """
    # Ideal resistor impedance
    Z = R * np.ones_like(frequencies, dtype=complex)

    # Add noise only to real part
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, size=len(frequencies))
        Z = (R + noise) + 0j

    return Z
