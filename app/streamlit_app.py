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
from analysis.interpretation import characteristic_frequency, interpret_randles, cell_constant_parallel_plate, compare_fc_fapex
from analysis.features import extract_features
from export.eis_report import build_eis_report_blocks
from export.report_export import render_pdf, save_report, figure_to_png
from export.report_docx import render_docx, save_docx 

# Report formats offered in the export list: label -> MIME type of the download
REPORT_FORMATS = {
    "PDF": "application/pdf",
    "Word (.docx)": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

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
    ["Resistor (R)", "Capacitor (C)", "Series RC (R + 1/(jωC))","Randles (Rs + Rct‖Cdl)"],
)

# Initial parameter guesses
st.sidebar.markdown("### Initial parameter guesses")

if model_name == "Resistor (R)":
    R_guess = st.sidebar.number_input("R (Ω)", value=100.0, min_value=0.0)
    initial_params = [R_guess]
    model_func = Z_resistor(R_guess)
    param_labels = [("R", "Ω")]

elif model_name == "Capacitor (C)":
    C_guess = st.sidebar.number_input("C (F)", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [C_guess]
    model_func = Z_capacitor(C_guess)
    param_labels = [("C", "F")]

elif model_name == "Series RC (R + 1/(jωC))":
    R_guess = st.sidebar.number_input("R (Ω)", value=100.0, min_value=0.0)
    C_guess = st.sidebar.number_input("C (F)", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [R_guess, C_guess]
    model_func = Z_rc_series(R_guess, C_guess)
    param_labels = [("R", "Ω"), ("C", "F")]
    
else:
    RS_guess = st.sidebar.number_input("$R_S (Ω)$", value=10.0, min_value=0.0)
    Rct_guess = st.sidebar.number_input("$R_{ct} (Ω)$", value=100.0, min_value=0.0)    
    Cdl_guess = st.sidebar.number_input("$C_{dl} (F)$", value=1e-6, min_value=0.0, format="%.2e")
    initial_params = [RS_guess, Rct_guess, Cdl_guess]
    model_func = Z_randles(RS_guess, Rct_guess, Cdl_guess)
    param_labels = [("R_s", "Ω"), ("R_{ct}", "Ω"), ("C_{dl}", "F")]

# ---------------------------------------------------------
# Sidebar: inputs for the electrochemical interpretation
# (only meaningful for the Randles model: Rs, Rct, Cdl)
# A value of 0 means "not provided" -> that quantity is skipped, never guessed.
# ---------------------------------------------------------
if model_name.startswith("Randles"):
    st.sidebar.markdown("### Electrochemical interpretation")

    electrode_area_cm2 = st.sidebar.number_input(
        "Electrode area $(cm²)$", value=0.0, min_value=0.0, format="%.4g",
        help="True electroactive area. 0 = not provided.",
    )
    temperature_C = st.sidebar.number_input(
        "Temperature $(°C)$", value=25.0, min_value=-50.0, max_value=150.0,
    )
    n_electrons = st.sidebar.number_input(
        "Number of electrons $n$", value=0, min_value=0, step=1,
        help="Electrons transferred in the redox reaction. 0 = not provided.",
    )

    use_geometry = st.sidebar.checkbox("Cell geometry known (for conductivity)")
    cell_length_cm = 0.0
    cell_area_cm2 = 0.0
    if use_geometry:
        cell_length_cm = st.sidebar.number_input(
            "Electrode spacing $L (cm)$", value=0.0, min_value=0.0, format="%.4g"
        )
        cell_area_cm2 = st.sidebar.number_input(
            "Electrolyte cross-section $(cm²)$", value=0.0, min_value=0.0, format="%.4g",
            help="Cross-section of the electrolyte between the electrodes.",
        )

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
    # Every figure shown below is also stored here (as PNG bytes) for the PDF report
    report_figures = []

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Nyquist plot (data)")
        fig_nyq, ax_nyq = plt.subplots()

        # IMPORTANT: Z_data itself must stay untouched — it's reused later
        # for the Bode plot, the fit, and the RMSE/chi-square metrics.
        # Any rescaling for display purposes goes into a separate Z_plot.
        Z_plot = Z_data

        is_img_axis = model_name in ["Capacitor (C)", "Series RC (R + 1/(jωC))", "Randles (Rs + Rct‖Cdl)"]

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

        nyq_caption = "Nyquist plot (data)"
        if is_img_axis and scale_factor != 1:
            nyq_caption += f" - imaginary axis divided by {scale_factor}"
        report_figures.append((nyq_caption, figure_to_png(fig_nyq)))

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
        report_figures.append(("Bode plot (data)", figure_to_png(fig_bode)))
    
    if df_proc.isna().any().any() or not np.isfinite(df_proc.values).all():
      st.error("Fitting failed: your data contains NaN or infinite values. "
             "This usually happens due to smoothing or missing values in the CSV.")
      st.stop()
    
    # ---------------------------------------------------------
    # Model-free features (no fit): read directly from the data
    # ---------------------------------------------------------
    st.subheader("Model-free features (from the data, no fit)")

    # Use UNSMOOTHED data here: smoothing + dropna() removes the outermost
    # frequency points, and the intercepts depend exactly on those points.
    df_feat = preprocess_impedance(df_raw, smooth=False)
    f_feat = df_feat["frequency"].to_numpy(dtype=float)
    Z_feat = (df_feat["real"].to_numpy(dtype=float)
              + 1j * df_feat["imag"].to_numpy(dtype=float))
    
    feat = None

    try:
        feat = extract_features(f_feat, Z_feat)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("$R_{high}$", f"{feat.R_high:.4g} Ω")
        c2.metric("$R_{low}$", f"{feat.R_low:.4g} Ω")
        c3.metric("$R_{low} - R_{high}$", f"{feat.R_diff:.4g} Ω")
        c4.metric("$f_{apex}$", f"{feat.f_apex:.4g} Hz")

        st.caption(
            "Measured: real-axis values at both ends and the frequency of the "
            "maximum of $−Z''$. If the system behaves like a Randles circuit, "
            "$R_{high}$ ≈ $R_s$, $R_{low} - R_{high}$ ≈ $R_{ct}$, and $$f_{apex} = 1/(2π·R_{ct}·C_{dl})$$."
        )

        # Tell the user when a feature should not be trusted
        if not feat.R_high_reliable:
            st.warning("High-frequency end does not reach the real axis: $R_{high}$ is only an upper bound for $R_s$.")
        if not feat.R_low_reliable:
            st.warning("No low-frequency plateau on the real axis: $R_{low}$ is not an $R_s + R_{ct}$ estimate.")
        if not feat.apex_resolved:
            st.warning("The maximum of $−Z''$ is at the edge of the measured range: $f_{apex}$ is not resolved.")

    except ValueError as e:
        # e.g. a pure resistor has Z'' = 0 everywhere, so there is nothing to extract
        st.info(f"Features not available for this dataset: {e}")

    # ---------------------------------------------------------
    # Session state for fit results
    # ---------------------------------------------------------
    if "fit_results" not in st.session_state:
        st.session_state.fit_results = None

    # ---------------------------------------------------------
    # Run fitting only when button is pressed
    # ---------------------------------------------------------
    if fit_button:
        st.session_state.report_files = {}   # a new fit makes previous reports stale
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
            st.write(f"$p_{i+1} = {p:.4g}$")

        rmse_val = rmse_complex(Z_data, Z_fit)
        chi2_val = chi_square(Z_data, Z_fit)

        st.markdown(f"- **RMSE (complex):** `{rmse_val:.4g} Ω`")
        st.markdown(f"- **χ² (σ=1):** `{chi2_val:.4g}`")

        # Defaults for the report; the Randles block below fills them in.
        # The report simply skips what is empty.
        results = []
        check = None
        report_inputs = None

        # -----------------------------------------------------
        # Electrochemical interpretation (Randles model only)
        # -----------------------------------------------------
        # len(popt) == 3 guards against a stale fit from another model.
        if model_name.startswith("Randles") and len(popt) == 3:
            st.subheader("Electrochemical interpretation")
            st.caption(
                "Fitted electrical parameters are converted into electrochemical "
                "quantities. Each result is only as valid as its listed assumptions."
            )

            Rs_fit, Rct_fit, Cdl_fit = popt

            # Convert the "0 = not provided" inputs into None
            cell_constant = None
            if use_geometry and cell_length_cm > 0 and cell_area_cm2 > 0:
                cell_constant = cell_constant_parallel_plate(cell_length_cm, cell_area_cm2)

            try:
                results = interpret_randles(
                    Rs_fit, Rct_fit, Cdl_fit,
                    area_cm2=electrode_area_cm2 or None,
                    n=int(n_electrons) or None,
                    T_kelvin=temperature_C + 273.15,
                    cell_constant_per_cm=cell_constant,
                )
            except ValueError as e:
                st.error(f"Interpretation failed: {e}")
                results = []

            # User-provided values that the interpretation depends on (for the report)
            report_inputs = {"Temperature": f"{temperature_C:g} °C"}
            if electrode_area_cm2:
                report_inputs["Electrode area"] = f"{electrode_area_cm2:g} cm²"
            if n_electrons:
                report_inputs["Number of electrons n"] = int(n_electrons)
            if cell_constant is not None:
                report_inputs["Electrode spacing L"] = f"{cell_length_cm:g} cm"
                report_inputs["Electrolyte cross-section"] = f"{cell_area_cm2:g} cm²"

            for r in results:
                st.metric(r.name, f"{r.value:.4g} {r.unit}")
                with st.expander(f"Formula and assumptions: {r.name}"):
                    st.markdown(f"**Formula:**")
                    st.latex(r.formula)
                    st.markdown("**Assumptions**")
                    for a in r.assumptions:
                        st.markdown(f"- {a}")
                    if r.notes:
                        st.markdown("**Notes**")
                        for note in r.notes:
                            st.markdown(f"- {note}")
            
            # -------------------------------------------------
            # Cross-check: fitted f_c vs measured f_apex
            # -------------------------------------------------
            st.markdown("**Consistency check: fit vs data**")

            if feat is None or not feat.apex_resolved:
                st.info(
                    "No reliable $f_{apex}$ was measured (apex missing or at the "
                    "edge of the frequency range), so the fit cannot be "
                    "cross-checked against the data."
                )
            else:
                f_c_fit = characteristic_frequency(Rct_fit, Cdl_fit)
                check = compare_fc_fapex(f_c_fit, feat.f_apex)

                k1, k2, k3 = st.columns(3)
                k1.metric("$f_c$ (fit)", f"{check.f_c:.4g} Hz")
                k2.metric("$f_{apex}$ (data)", f"{check.f_apex:.4g} Hz")
                k3.metric("Difference", f"{100 * check.rel_diff:.1f} %")

                if check.consistent:
                    st.success(
                        "The fit and the data agree on the time constant. "
                        "This supports the single-semicircle model, but does not "
                        "prove it."
                    )
                else:
                    st.warning(
                        "The fitted $f_c$ and the measured $f_{apex}$ disagree. "
                        "Possible reasons: a depressed semicircle (CPE instead of "
                        "an ideal capacitor), overlapping time constants, a "
                        "diffusion (Warburg) tail, a poor initial guess or fit, or "
                        "coarse frequency spacing. Treat $\\tau$, $j_0$ and "
                        "$C_{dl}/A$ with caution."
                    )

            # Tell the user what is missing instead of silently hiding it
            if not electrode_area_cm2:
                st.info("Enter the electrode area to get $C_{dl}/A$ and $j_0$.")
            elif not n_electrons:
                st.info("Enter the number of electrons $n$ to get $j_0$.")
            if use_geometry and cell_constant is None:
                st.info("Enter both the spacing L and the cross-section to get conductivity.")

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
        report_figures.append(("Nyquist: data vs fitted model", figure_to_png(fig_nyq_fit)))

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
        report_figures.append(("Bode: data vs fitted model", figure_to_png(fig_bode_fit)))

        # -----------------------------------------------------
        # Export the whole analysis as a PDF report
        # -----------------------------------------------------
        st.subheader("Export report")
        st.caption(
            "PDF and Word report with the fit parameters, the measured features, "
            "the interpretation (formulas rendered, LaTeX source below each) and "
            "the figures shown above."
        )

        # Format list: the user picks ONE format, and only that file is built.
        export_format = st.selectbox("Report format", list(REPORT_FORMATS))

        if st.button(f"Generate {export_format} report"):
            try:
                # 1) what the report says (independent of the file format)
                blocks = build_eis_report_blocks(
                    model_name=model_name,
                    popt=popt,
                    rmse=rmse_val,
                    chi2=chi2_val,
                    param_labels=param_labels,
                    feat=feat,
                    results=results,
                    inputs=report_inputs,
                    check=check,
                    figures=report_figures,        # list of (caption, PNG bytes)
                    data_name=uploaded_file.name,
                )
                # 2) how it is drawn: only the chosen format is created
                base_name = f"{Path(uploaded_file.name).stem}_{model_name}"
                if export_format == "PDF":
                    path = save_report(render_pdf(blocks), base_name)
                else:
                    path = save_docx(render_docx(blocks), base_name)

                # one entry per format, so switching the list back and forth
                # does not lose a report that was already generated
                if "report_files" not in st.session_state:
                    st.session_state.report_files = {}
                st.session_state.report_files[export_format] = path
            except Exception as e:
                # e.g. a missing DejaVu font in fonts/, or python-docx not installed
                st.error(f"Report export failed: {e}")

        # Paths live in session_state so the download button survives the rerun
        # that Streamlit triggers when it is clicked.
        path = st.session_state.get("report_files", {}).get(export_format)
        if path:
            with open(path, "rb") as fh:
                st.download_button(
                    f"Download {export_format}",
                    fh.read(),
                    file_name=Path(path).name,
                    mime=REPORT_FORMATS[export_format],
                )

else:
    st.info("Upload a CSV file in the sidebar to begin.")
