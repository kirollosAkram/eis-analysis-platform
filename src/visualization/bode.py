import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

def load_impedance_csv(filepath: str):
    df = pd.read_csv(filepath)
    df = df.sort_values("frequency")
    freq = df["frequency"].values
    real = df["real"].values
    imag = df["imag"].values
    Z = real + 1j * imag
    return freq, Z

def plot_bode_magnitude(freq, Z, label=None, save_path=None):
    mag = np.abs(Z)

    plt.figure(figsize=(7, 5))
    plt.semilogx(freq, mag, "o-", label=label)
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("|Z| [Ω]")
    plt.title("Bode Magnitude Plot")
    plt.grid(True, which="both")
    if label:
        plt.legend()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300)

    plt.show()

def plot_bode_phase(freq, Z, label=None, save_path=None):
    phase = np.angle(Z, deg=True)

    plt.figure(figsize=(7, 5))
    plt.semilogx(freq, phase, "o-", label=label)
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Phase [°]")
    plt.title("Bode Phase Plot")
    plt.grid(True, which="both")
    if label:
        plt.legend()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300)

    plt.show()

def bode_from_csv(filepath, label=None, save_mag_path=None, save_phase_path=None):
    freq, Z = load_impedance_csv(filepath)
    plot_bode_magnitude(freq, Z, label=label, save_path=save_mag_path)
    plot_bode_phase(freq, Z, label=label, save_path=save_phase_path)
