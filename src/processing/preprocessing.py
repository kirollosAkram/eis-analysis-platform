import pandas as pd
import numpy as np
from pathlib import Path

REQUIRED_COLUMNS = ["frequency", "real", "imag"]


def load_raw_csv(filepath: str) -> pd.DataFrame:
    """
    Load raw impedance CSV and validate required columns.
    """
    df = pd.read_csv(filepath)

    # Validate columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Sort by frequency
    df = df.sort_values("frequency").reset_index(drop=True)

    return df


def remove_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows with NaN, inf, or negative frequencies.
    """
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    df = df[df["frequency"] > 0]

    return df.reset_index(drop=True)


def apply_smoothing(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Apply simple moving-average smoothing to real and imaginary parts.
    """
    if df["imag"].abs().max() < 1000:  # only smooth small signals
        df["real"] = df["real"].rolling(window, center=True).mean().fillna(df["real"])
        df["imag"] = df["imag"].rolling(window=window, center=True).mean()

    return df


def preprocess(filepath: str, smooth: bool = False, window: int = 3) -> pd.DataFrame:
    """
    Full preprocessing pipeline.
    """
    df = load_raw_csv(filepath)
    df = remove_invalid_rows(df)

    if smooth:
        df = apply_smoothing(df, window)

    return df


def save_processed(df: pd.DataFrame, output_path: str):
    """
    Save processed dataset to data/processed/.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def preprocess_impedance(
    file_or_df, smooth: bool = False, window: int = 3
) -> pd.DataFrame:
    """
    High-level preprocessing wrapper for impedance datasets.

    This function allows the Streamlit app (or any other interface)
    to preprocess impedance data whether it comes from:
    - a CSV file path (string)
    - a pandas DataFrame already loaded in memory

    Steps:
    1. Load raw CSV (if needed)
    2. Remove invalid rows (NaN, inf, negative frequencies)
    3. Apply optional smoothing
    4. Return clean DataFrame

    Parameters
    ----------
    file_or_df : str or pd.DataFrame
        CSV filepath or already-loaded DataFrame.
    smooth : bool
        Whether to apply moving-average smoothing.
    window : int
        Smoothing window size.

    Returns
    -------
    pd.DataFrame
        Cleaned impedance dataset.
    """

    # Case 1: user passed a filepath
    if isinstance(file_or_df, str):
        df = load_raw_csv(file_or_df)

    # Case 2: user passed a DataFrame (Streamlit upload)
    elif isinstance(file_or_df, pd.DataFrame):
        df = file_or_df.copy()

        # Validate required columns
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Sort by frequency
        df = df.sort_values("frequency").reset_index(drop=True)

    else:
        raise TypeError(
            "preprocess_impedance expects a filepath or a pandas DataFrame."
        )

    # Apply cleaning steps
    df = remove_invalid_rows(df)

    # Optional smoothing
    if smooth:
        df = apply_smoothing(df, window)
        
    df = df.dropna()
    
    return df.reset_index(drop=True)
