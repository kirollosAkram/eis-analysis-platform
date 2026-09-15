import numpy as np

def residuals(Z_data: np.ndarray, Z_model: np.ndarray):
    """
    Complex residuals: Z_data - Z_model
    It calculates the difference between an observed value and a predicted value.
    """
    return Z_data - Z_model

def rmse_complex(Z_data: np.ndarray, Z_model: np.ndarray):
    """
    RMSE in the complex plane.
    It is a statistical measure used to evaluate the difference between the values predicted by a model and the actual values.
    """
    res = residuals(Z_data, Z_model)
    return np.sqrt(np.mean(np.abs(res)**2))

def mae_complex(Z_data: np.ndarray, Z_model: np.ndarray):
    """
    Mean absolute error in the complex plane.
    """
    res = residuals(Z_data, Z_model)
    return np.mean(np.abs(res))

def chi_square(Z_data: np.ndarray, Z_model: np.ndarray, sigma: float = 1.0):
    """
    Chi-square error metric.
    sigma = assumed measurement noise level.
    """
    res = residuals(Z_data, Z_model)
    return np.sum((np.abs(res) / sigma)**2)
