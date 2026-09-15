"""
capacitor.py — Simulation of ideal capacitor impedance

Z_C = 1 / (j * omega * C)
"""

import numpy as np

def simulate_capacitor(C: float, frequencies: np.ndarray, noise_level: float = 0.0):
    """
    Simulate impedance of an ideal capacitor.

    Parameters
    ----------
    C : float
        Capacitance in farads.
    frequencies : np.ndarray
        Frequency array in Hz.
    noise_level : float
        Standard deviation of Gaussian noise added to imag(Z).

    Returns
    -------
    Z : np.ndarray
        Complex impedance array.
    """
    omega = 2 * np.pi * frequencies
    Z = 1 / (1j * omega * C)

    # Add noise to imaginary part
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, size=len(frequencies))
        Z = Z + 1j * noise

    return Z
