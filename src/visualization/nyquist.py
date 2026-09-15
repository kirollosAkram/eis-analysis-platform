import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

def load_impedance_csv(filepath: str):
    """
    Load impedance CSV file containing:
    frequency, real, imag
    """
    df = pd.read_csv(filepath)
    df = df.sort_values("frequency")
    return df["frequency"].values, df["real"].values, df["imag"].values

def plot_nyquist(real, imag, label=None, save_path=None):
    """
    Generate a Nyquist plot (Z' vs -Z'').
    """
    plt.figure(figsize=(6, 6))
    plt.plot(real, -imag, "o-", label=label)

    plt.xlabel("Z' (Real Impedance) [Ω]")
    plt.ylabel("-Z'' (Imaginary Impedance) [Ω]")
    plt.title("Nyquist Plot")
    plt.grid(True)
    if label:
        plt.legend()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300)

    plt.show()

def nyquist_from_csv(filepath, label=None, save_path=None):
    freq, real, imag = load_impedance_csv(filepath)
    plot_nyquist(real, imag, label=label, save_path=save_path)
