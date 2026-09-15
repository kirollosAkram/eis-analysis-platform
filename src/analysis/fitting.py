import numpy as np
from scipy.optimize import curve_fit

def _complex_to_stacked(z: np.ndarray):
    """
    Convert complex impedance array into stacked real+imag vector.
    Used so SciPy can fit complex-valued functions.
    """
    return np.concatenate([z.real, z.imag])

def _stacked_model(frequencies: np.ndarray, *params, model_func=None):
    """
    Wrapper so SciPy can evaluate a complex model and return stacked real+imag.
    """
    Z = model_func(frequencies, *params)
    return _complex_to_stacked(Z)

def fit_model(frequencies: np.ndarray,
              Z_data: np.ndarray,
              model_func,
              initial_params: list):
    """
    Fit an equivalent circuit model using SciPy.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency vector (Hz)
    Z_data : np.ndarray
        Complex impedance data
    model_func : callable
        Function Z(f, *params) from equivalent_circuits.py
    initial_params : list
        Initial guess for parameters

    Returns
    -------
    popt : np.ndarray
        Best-fit parameters
    pcov : np.ndarray
        Covariance matrix
    """

    ydata = _complex_to_stacked(Z_data)

    def wrapped_model(freq, *params):
        return _stacked_model(freq, *params, model_func=model_func)

    popt, pcov = curve_fit(
        wrapped_model,
        frequencies,
        ydata,
        p0=initial_params,
        maxfev=20000
    )

    return popt, pcov
