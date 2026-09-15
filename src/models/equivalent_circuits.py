import numpy as np


# Basic Components

def Z_resistor(R):
    """
    Impedance of a pure resistor.
    Parameters
    ----------
    R : float
        Resistance in ohms.

    Returns
    -------
    function
        A function Z(f) returning complex impedance.
    """
    def model(f, R):
        return R * np.ones_like(f, dtype=complex)
    return model


def Z_capacitor(C):
    """
    Impedance of a pure capacitor.
    Parameters
    ----------
    C : float
        Capacitance in farads.

    Returns
    -------
    function
        A function Z(f) returning complex impedance.
    """
    def model(f, C):
        omega = 2 * np.pi * f
        return 1 / (1j * omega * C)
    return model


# RC Circuits

def Z_rc_series(R, C):
    """
    Series RC circuit: Z = R + 1/(jωC)
    """
    def model(f, R, C):
        omega = 2 * np.pi * f
        Zc = 1 / (1j * omega * C)
        return R + Zc
    return model


def Z_rc_parallel(R, C):
    """
    Parallel RC circuit: Z = 1 / (1/R + jωC)
    """
    def model(f, R, C):
        omega = 2 * np.pi * f
        Y = (1 / R) + (1j * omega * C)  # admittance
        return 1 / Y
    return model



# Randles Circuit (Simplified)

def Z_randles(Rs, Rct, Cdl):
    """
    Simplified Randles circuit:
        Rs in series with (Rct || Cdl)

    Equivalent impedance:
        Z = Rs + 1 / (1/Rct + jωCdl)
    """
    def model(f, Rs, Rct, Cdl):
        omega = 2 * np.pi * f
        Y_parallel = (1 / Rct) + (1j * omega * Cdl)
        Z_parallel = 1 / Y_parallel
        return Rs + Z_parallel
    return model


# Utility: Evaluate a circuit model

def evaluate_model(model, frequencies):
    """
    Evaluate any circuit model on a frequency vector.

    Parameters
    ----------
    model : function
        A model returned by Z_resistor, Z_capacitor, etc.
    frequencies : array-like
        Frequency vector in Hz.

    Returns
    -------
    np.ndarray
        Complex impedance values.
    """
    return model(frequencies)