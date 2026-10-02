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
              initial_params: list,
              bounds=None):
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
    bounds : tuple (lower, upper), optional
        Limits for each parameter. If None, every parameter is forced to be
        strictly positive (R and C cannot be negative or zero in a physical
        circuit, and a value of exactly 0 would cause a division by zero
        in models such as 1/R).

    Returns
    -------
    popt : np.ndarray
        Best-fit parameters
    pcov : np.ndarray
        Covariance matrix
    """

    ydata = _complex_to_stacked(Z_data)
    p0 = np.asarray(initial_params, dtype=float)

    if bounds is None:
        # Tiny positive lower bound instead of 0 (avoids 1/0 in the models)
        bounds = (np.full_like(p0, 1e-15), np.full_like(p0, np.inf))

    def wrapped_model(freq, *params):
        return _stacked_model(freq, *params, model_func=model_func)

    # Giving bounds makes SciPy switch from the 'lm' to the 'trf' algorithm.
    # x_scale="jac" tells it to rescale each parameter automatically — needed
    # because our parameters live on very different scales
    # (R ~ 10-1000 ohm, C ~ 1e-6 F).
    popt, pcov = curve_fit(
        wrapped_model,
        frequencies,
        ydata,
        p0=p0,
        bounds=bounds,
        x_scale="jac",
        maxfev=20000
    )

    return popt, pcov
