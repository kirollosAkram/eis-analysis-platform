import sys
from pathlib import Path
import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Import src modules
# ---------------------------------------------------------
project_root = Path(__file__).resolve().parents[1]
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from processing.preprocessing import preprocess_impedance
from models.equivalent_circuits import Z_resistor, Z_capacitor, Z_rc_series, Z_randles
from analysis.fitting import fit_model
from analysis.metrics import rmse_complex, chi_square

# ---------------------------------------------------------
# Streamlit page config
# ---------------------------------------------------------
st.set_page_config(page_title="EIS Data Analysis Platform", layout="wide")
st.title("⚡ Electrochemical Impedance Spectroscopy (EIS) Analyzer")

st.markdown("""
Upload an impedance dataset, choose an equivalent circuit,
fit the parameters with SciPy, and visualise Nyquist/Bode plots.
""")

# ---------------------------------------------------------
# Sidebar: Data & Model
# ---------------------------------------------------------
st.sidebar.header("Data & Model")

uploaded_file = st.sidebar.file_uploader(
    "Upload impedance CSV", type=["csv"], help="Must contain: frequency, real, imag"
)

model_name = st.sidebar.selectbox(
    "Equivalent circuit model",
    ["Resistor (R)", "Capacitor (C)", "Series RC (R + 1/(jωC))","Randle (Rs + Rct‖Cdl)"],
)

# Initial parameter guesses
st.sidebar.markdown("### Initial parameter guesses")

if model_name == "Resistor (R)":
    R_guess = st.sidebar.number_input("R (Ω)", value=100.0, min_value=0.0)
    initial_params = [R_guess]
    model_func = Z_resistor(R_guess)

elif model_name == "Capacitor (C)":
    C_guess = st.sidebar.number_input("C (F)", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [C_guess]
    model_func = Z_capacitor(C_guess)

elif model_name == "Series RC (R + 1/(jωC))":
    R_guess = st.sidebar.number_input("R (Ω)", value=100.0, min_value=0.0)
    C_guess = st.sidebar.number_input("C (F)", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [R_guess, C_guess]
    model_func = Z_rc_series(R_guess, C_guess)
    
else:
    RS_guess = st.sidebar.number_input("$R_S (Ω)$", value=10.0, min_value=0.0)
    Rct_guess = st.sidebar.number_input("$R_{ct} (Ω)$", value=100.0, min_value=0.0)    
    Cdl_guess = st.sidebar.number_input("$C_{dl} (F)$", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [RS_guess, Rct_guess, Cdl_guess]
    model_func = Z_randles(RS_guess, Rct_guess, Cdl_guess)

fit_button = st.sidebar.button("Run fit")

# ---------------------------------------------------------
# Load and preprocess data
# ---------------------------------------------------------
if uploaded_file is not None:
    bytes_data = uploaded_file.read()
    df_raw = pd.read_csv(io.BytesIO(bytes_data))

    st.subheader("Raw data preview")
    st.dataframe(df_raw.head())

    # Preprocess using your wrapper
    df_proc = preprocess_impedance(df_raw, smooth=True, window=5)

    # Extract arrays as pure NumPy
    frequencies = df_proc["frequency"].to_numpy(dtype=float)
    real = df_proc["real"].to_numpy(dtype=float)
    imag = df_proc["imag"].to_numpy(dtype=float)
    
    Z_data = real + 1j * imag

    # ---------------------------------------------------------
    # Show raw Nyquist & Bode plots
    # ---------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Nyquist plot (data)")
        fig_nyq, ax_nyq = plt.subplots()

        # IMPORTANT: Z_data itself must stay untouched — it's reused later
        # for the Bode plot, the fit, and the RMSE/chi-square metrics.
        # Any rescaling for display purposes goes into a separate Z_plot.
        Z_plot = Z_data

        is_img_axis = model_name in ["Capacitor (C)", "Series RC (R + 1/(jωC))", "Randle (Rs + Rct‖Cdl)"]

        if is_img_axis:
            scale_factor = st.selectbox(
                "Imaginary axis scaling (divides -Z'' for readability)",
                [1, 10, 100, 1000, 10000, 100000],
            )
            Z_plot = real + 1j * (imag / scale_factor)
            y_label = f"$-Z''\\,/\\,{scale_factor}$ (Ω)" if scale_factor != 1 else r"$-Z'' \, (\Omega)$"
        else:
            y_label = r"$-Z'' \, (\Omega)$"

        ax_nyq.plot(Z_plot.real, -Z_plot.imag, "o-")
        ax_nyq.set_xlabel(r"$Z' \, (\Omega)$")
        ax_nyq.set_ylabel(y_label)

        if model_name == "Resistor (R)":
            ax_nyq.set_aspect("equal", "box")
        else:
            ax_nyq.set_aspect("auto")
            # Autoscale to the ACTUAL data range instead of a fixed window —
            # a fixed range (e.g. -5000 to 0) crushes the curve into a corner
            # whenever the real data (or the rescaled version) doesn't span it.
            x_min, x_max = Z_plot.real.min(), Z_plot.real.max()
            y_min, y_max = (-Z_plot.imag).min(), (-Z_plot.imag).max()
            x_pad = 0.1 * (x_max - x_min) if x_max > x_min else 1.0
            y_pad = 0.1 * (y_max - y_min) if y_max > y_min else 1.0
            ax_nyq.set_xlim(float(x_min - x_pad), float(x_max + x_pad))
            ax_nyq.set_ylim(float(y_min - y_pad), float(y_max + y_pad))

        ax_nyq.grid(True)
        st.pyplot(fig_nyq)

    with col2:
        st.subheader("Bode plot (data)")
        mag = np.abs(Z_data)
        phase = np.angle(Z_data, deg=True)

        fig_bode, ax_bode = plt.subplots(2, 1, figsize=(5, 6), sharex=True)
        ax_bode[0].loglog(frequencies, mag, "o")
        ax_bode[0].set_ylabel(r"$|Z| \, (\Omega)$")
        ax_bode[0].grid(True)

        ax_bode[1].semilogx(frequencies, phase, "o")
        ax_bode[1].set_xlabel("Frequency (Hz)")
        ax_bode[1].set_ylabel("Phase (°)")
        ax_bode[1].grid(True)

        st.pyplot(fig_bode)
    
    if df_proc.isna().any().any() or not np.isfinite(df_proc.values).all():
      st.error("Fitting failed: your data contains NaN or infinite values. "
             "This usually happens due to smoothing or missing values in the CSV.")
      st.stop()

    # ---------------------------------------------------------
    # Session state for fit results
    # ---------------------------------------------------------
    if "fit_results" not in st.session_state:
        st.session_state.fit_results = None

    # ---------------------------------------------------------
    # Run fitting only when button is pressed
    # ---------------------------------------------------------
    if fit_button:
        try:
            popt, pcov = fit_model(frequencies, Z_data, model_func, initial_params)
            Z_fit = model_func(frequencies, *popt)

            st.session_state.fit_results = {"popt": popt, "pcov": pcov, "Z_fit": Z_fit}

        except Exception as e:
            st.error(f"Fitting failed: {e}")
            st.session_state.fit_results = None

    # ---------------------------------------------------------
    # Display results only if fitting was done
    # ---------------------------------------------------------
    if st.session_state.fit_results is not None:
        popt = st.session_state.fit_results["popt"]
        Z_fit = st.session_state.fit_results["Z_fit"]

    stale_fit = (
        st.session_state.fit_results is not None
        and len(st.session_state.fit_results["Z_fit"]) != len(Z_data)
    )
    if stale_fit:
        st.session_state.fit_results = None
        st.info("Data or settings changed since the last fit — press **Run fit** again.")

    if st.session_state.fit_results is not None:
        popt = st.session_state.fit_results["popt"]
        Z_fit = st.session_state.fit_results["Z_fit"]

        st.subheader("Fitting results")

        for i, p in enumerate(popt):
            st.write(f"p{i+1} = {p:.4g}")

        rmse_val = rmse_complex(Z_data, Z_fit)
        chi2_val = chi_square(Z_data, Z_fit)

        st.markdown(f"- **RMSE (complex):** `{rmse_val:.4g} Ω`")
        st.markdown(f"- **χ² (σ=1):** `{chi2_val:.4g}`")

        # Nyquist comparison
        st.subheader("Nyquist: data vs fitted model")
        fig_nyq_fit, ax_nyq_fit = plt.subplots()
        ax_nyq_fit.plot(Z_data.real, -Z_data.imag, "o", label="Data")
        ax_nyq_fit.plot(Z_fit.real, -Z_fit.imag, "-", label="Fit")
        ax_nyq_fit.set_xlabel(r"$Z' \, (\Omega)$")
        ax_nyq_fit.set_ylabel(r"$-Z'' \, (\Omega)$")

        if model_name == "Resistor (R)":
            ax_nyq_fit.set_aspect("equal", "box")

        else:
            ax_nyq_fit.set_aspect("auto")

        ax_nyq_fit.grid(True)
        ax_nyq_fit.legend()
        st.pyplot(fig_nyq_fit)

        # Bode comparison
        st.subheader("Bode: data vs fitted model")
        mag_fit = np.abs(Z_fit)
        phase_fit = np.angle(Z_fit, deg=True)

        fig_bode_fit, ax_bode_fit = plt.subplots(2, 1, figsize=(5, 6), sharex=True)
        ax_bode_fit[0].loglog(frequencies, mag, "o", label="Data")
        ax_bode_fit[0].loglog(frequencies, mag_fit, "-", label="Fit")
        ax_bode_fit[0].set_ylabel(r"$|Z| \, (\Omega)$")
        ax_bode_fit[0].set_xlabel("Frequency (Hz)")
        ax_bode_fit[0].legend()
        ax_bode_fit[0].grid(True)

        ax_bode_fit[1].semilogx(frequencies, phase, "o", label="Data")
        ax_bode_fit[1].semilogx(frequencies, phase_fit, "-", label="Fit")
        ax_bode_fit[1].set_ylabel("Phase (°)")
        ax_bode_fit[1].set_xlabel("Frequency (Hz)")
        ax_bode_fit[1].legend()
        ax_bode_fit[1].grid(True)

        st.pyplot(fig_bode_fit)

else:
    st.info("Upload a CSV file in the sidebar to begin.")
