# Methodology  
_Electrochemical Impedance Spectroscopy (EIS) Analysis Platform_

This document describes the methodological foundations of the EIS Analysis Platform.  
It explains how the project structures data, simulations, visualisation, and model fitting in a reproducible and modular workflow.

---

## 1. Overview

Electrochemical Impedance Spectroscopy (EIS) is a frequency‑domain technique used to characterise electrochemical systems by applying a small AC perturbation and measuring the system’s complex impedance.  
The platform provides:

- Controlled synthetic datasets (resistor, capacitor, RC circuit)
- Tools for loading and preprocessing raw measurement data
- Visualisation modules (Nyquist, Bode)
- Equivalent‑circuit modelling and parameter fitting
- A reproducible notebook‑based workflow

This methodology ensures that each stage of the project is built upon the previous one., forming a coherent pipeline from fundamentals → simulation → visualisation → fitting → interpretation.

---

## 2. Project Architecture

The project follows a modular structure:

```
eis-analysis-platform/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── simulated/
│
├── docs/
│   ├── methodology.md
│   ├── eis_fundamentals.md
│   └── equivalent_circuits.md
│
├── notebooks/
│   ├── 01_eis_fundamentals.ipynb
│   ├── 02_resistor_simulation.ipynb
│   ├── 03_capacitor_simulation.ipynb
│   ├── 04_rc_simulation.ipynb
│   ├── 05_visualisation.ipynb
│   └── 06_circuit_fitting.ipynb
│
├── src/
│   ├── simulation/
│   ├── preprocessing/
│   ├── visualisation/
│   ├── models/
│   └── analysis/
│
├── app/
│   └── streamlit_app.py
│
├── results/
│   ├── figures/

```
---

## 3. Data Flow

### 3.1 Synthetic Data Generation  
Synthetic datasets are generated using analytical impedance expressions:

- **Resistor:**  
  $$Z_R = R$$

- **Capacitor:**  
  $$Z_C = \frac{1}{j \omega C}$$

- **Series RC:**  
  $$Z_{RC} = R + \frac{1}{j \omega C}$$

These datasets allow controlled experiments before working with real measurements.

### 3.2 Raw Data Loading  
Raw CSV files must contain:

frequency, real, imag


Validation ensures:

- monotonic frequency ordering  
- no missing values  
- correct numeric types  

### 3.3 Preprocessing  
Preprocessing includes:

- sorting by frequency  
- removing invalid rows  
- computing magnitude and phase  
- exporting cleaned datasets to `data/processed/`

---

## 4. Visualisation Methodology

Two canonical EIS plots are used:

### Nyquist Plot  
- X-axis: $\Re(Z)$  
- Y-axis: $-\Im(Z)$  
- Shows geometric features (semicircles, straight lines)

### Bode Plot  
- Magnitude: $|Z|$ vs frequency  
- Phase: $\varphi$ vs frequency  
- Highlights frequency-dependent behaviour

Visualisation modules ensure consistent styling and reproducibility.

---

## 5. Equivalent Circuit Modelling

Equivalent circuits translate physical behaviour into mathematical models.  
The platform supports:

- Ideal $R$  
- Ideal $C$  
- Series $RC$  
- Extendable to $R||C$, $R(Q)$ models, Warburg elements, etc.

Each model provides:

- Analytical impedance function  
- Parameter vector  
- Frequency-dependent evaluation

---

## 6. Parameter Fitting

Parameter estimation uses nonlinear least squares:

- **RMSE** evaluates absolute error  
- **Chi-square** evaluates error weighted by measurement variance

Fitting workflow:

1. Load dataset  
2. Select circuit model  
3. Compute predicted impedance  
4. Minimise error metric  
5. Compare fitted vs measured curves  
6. Interpret physical meaning

---

## 7. Reproducibility

The project ensures reproducibility through:

- Version-controlled notebooks  
- Deterministic synthetic datasets  
- Modular Python functions  
- Clear documentation in `docs/`

---

## 8. Streamlit Application

An optional Streamlit UI allows:

- Uploading CSV files  
- Visualising Nyquist/Bode plots  
- Running circuit fitting  
- Exporting results

This forms the final user-facing layer of the platform.

---

## 9. Conclusion

This methodology defines a complete, modular, and reproducible workflow for EIS data analysis.  
It supports both educational exploration and professional instrumentation tasks.


