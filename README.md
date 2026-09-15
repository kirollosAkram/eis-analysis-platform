# Electrochemical Impedance Spectroscopy (EIS) Analysis Platform

An open‑source Python platform for **simulating**, **processing**, **visualising**, and **modelling** Electrochemical Impedance Spectroscopy (EIS) data.  
Designed for education, research, and instrumentation prototyping.

---

## 📌 Features

### 1. Impedance Simulation
Generate controlled synthetic datasets:
- Ideal resistor $(R)$
- Ideal capacitor $(C)$
- Series RC circuit $(R + 1/(jωC))$

Modules:  
`src/simulation/resistor.py`, `src/simulation/capacitor.py`, `src/simulation/rc_circuit.py`

---

### 2. Data Loading & Preprocessing
Tools for:
- Validating raw CSV files
- Removing invalid rows
- Optional smoothing
- Exporting cleaned datasets

Module:  
`src/preprocessing/preprocessing.py`

---

### 3. Visualisation
Publication‑quality plots:
- **Nyquist** $(Z′$ vs $−Z″)$
- **Bode magnitude** $(|Z|)$
- **Bode phase** $(∠Z)$

Modules:  
`src/visualisation/nyquist.py`, `src/visualisation/bode.py`

---

### 4. Equivalent Circuit Modelling
Analytical impedance functions:
- $R$, $C$
- Series $RC$
- Parallel $RC$
- Randles circuit

Module:  
`src/models/equivalent_circuits.py`

---

### 5. Parameter Fitting
Nonlinear least‑squares fitting using SciPy:
- RMSE
- Chi‑square
- Overlay plots (data vs model)

Module:  
`src/analysis/fitting.py`

---

### 6. Streamlit Application
Interactive web interface:
- Upload CSV
- Visualise Nyquist/Bode
- Select circuit model
- Fit parameters
- Display metrics

App:  
`app/streamlit_app.py`

---

## 📁 Repository Structure

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
│
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

---

## 🚀 Installation

```bash
git clone https://github.com/kirollosAkram/eis-analysis-platform.git
cd eis-analysis-platform
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
