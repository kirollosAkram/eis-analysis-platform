# EIS Data Analysis Platform

**Electrochemical Impedance Spectroscopy: simulation, equivalent-circuit modelling, parameter fitting and electrochemical interpretation.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![SciPy](https://img.shields.io/badge/Optimisation-SciPy-green)
![Streamlit](https://img.shields.io/badge/Interface-Streamlit-red)
![Status](https://img.shields.io/badge/Status-in%20development-orange)

---

## Table of contents

1. [Scientific background](#1-scientific-background)
2. [Project objectives](#2-project-objectives)
3. [Methodology](#3-methodology)
4. [Repository structure](#4-repository-structure)
5. [Installation and usage](#5-installation-and-usage)
6. [Data format](#6-data-format)
7. [Expected results](#7-expected-results)
8. [Limitations and assumptions](#8-limitations-and-assumptions)
9. [Skills developed](#9-skills-developed)
10. [Future work](#10-future-work)
11. [References](#11-references)
12. [Author and license](#12-author-and-license)

---

## 1. Scientific background

### 1.1 Electrochemical Impedance Spectroscopy (EIS)

EIS is a **non-destructive** characterisation technique. A small-amplitude sinusoidal perturbation (voltage or current) is applied to an electrochemical system, and the response is measured over a wide range of frequencies. The ratio of voltage to current defines the **complex impedance**:

$$
Z(\omega) = \frac{V(\omega)}{I(\omega)} = Z' + jZ'' , \qquad \omega = 2\pi f
$$

where $Z'$ is the real part (resistive behaviour) and $Z''$ the imaginary part (reactive behaviour, capacitive or inductive).

Because each physical process (ionic transport, charge transfer, double-layer charging, diffusion) has its own characteristic time scale, EIS makes it possible to **separate these contributions in the frequency domain**. It is used in corrosion studies, batteries, fuel cells, electrochemical sensors and biosensors, and in the characterisation of coatings and interfaces.

### 1.2 Equivalent-circuit modelling

Spectra are classically interpreted through an **equivalent circuit**: a network of ideal electrical elements (resistors, capacitors) whose frequency response reproduces that of the measured system.

| Element | Impedance | Usual physical meaning |
|---|---|---|
| Resistor $R$ | $Z_R = R$ | Electrolyte resistance, charge-transfer resistance |
| Capacitor $C$ | $Z_C = \dfrac{1}{j\omega C}$ | Electrochemical double-layer capacitance |
| $R$ in series with $C$ | $Z = R + \dfrac{1}{j\omega C}$ | Ideal blocking interface |
| $R \parallel C$ | $Z = \dfrac{1}{1/R + j\omega C}$ | A single-time-constant process |
| **Simplified Randles circuit** | $Z = R_s + \dfrac{1}{1/R_{ct} + j\omega C_{dl}}$ | Electrolyte + electrode/solution interface |

The simplified Randles circuit, $R_s + (R_{ct} \parallel C_{dl})$, is the central model of this project. It produces a **semicircle** in the Nyquist plot whose characteristic quantities can be read directly:

- high-frequency intercept with the real axis: $R_s$;
- semicircle diameter: $R_{ct}$;
- apex frequency: $f_{apex} = \dfrac{1}{2\pi R_{ct} C_{dl}}$.

### 1.3 Problem statement

An equivalent-circuit fit yields **electrical parameters** ($R_s$, $R_{ct}$, $C_{dl}$). These values are not, in themselves, chemical information. Going from them to electrochemical quantities (exchange current density, specific capacitance, conductivity) requires **explicit assumptions** about the system under study. This project aims to make that distinction visible in both the code and the interface.

---

## 2. Project objectives

**General objective.** Build a reproducible analysis pipeline, from the raw measurement file to a documented electrochemical interpretation, while keeping a strict separation between what is measured, what is fitted and what is interpreted.

**Specific objectives.**

1. **Understand and simulate** the frequency responses of basic elements and simple circuits (resistor, capacitor, series RC, Randles).
2. **Preprocess** experimental impedance data: format validation, removal of invalid values, optional smoothing.
3. **Visualise** spectra: Nyquist ($Z'$ vs $-Z''$) and Bode (magnitude and phase) plots.
4. **Extract model-free features** directly from the data: $R_{high}$, $R_{low}$, $R_{low}-R_{high}$, $f_{apex}$.
5. **Fit** an equivalent circuit by non-linear least squares and **quantify fit quality** (RMSE, MAE, $\chi^2$).
6. **Interpret** the fitted parameters as derived electrochemical quantities, each accompanied by its formula, its validity assumptions and data-dependent remarks.
7. **Expose everything** through an interactive application.

---

## 3. Methodology

The processing pipeline is organised into distinct levels, on purpose.

```
 Raw data (CSV)
        │
        ▼
 ┌─────────────────────┐
 │ 1. Preprocessing    │  validation, cleaning, optional smoothing
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 2. Measurable       │  model-free:
 │    features         │  R_high, R_low, f_apex
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 3. Fitting          │  electrical parameters:
 │    (equiv. circuit) │  Rs, Rct, Cdl  + RMSE, χ²
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 4. Electrochemical  │  derived quantities, each with
 │    interpretation   │  formula + assumptions + remarks
 └─────────────────────┘
```

### 3.1 Preprocessing (`preprocessing.py`)

- Validation of the required columns (`frequency`, `real`, `imag`) and sorting by increasing frequency.
- Removal of rows containing `NaN`, `±inf` or non-strictly-positive frequencies.
- Optional smoothing by a centred moving average, applied only to small-amplitude signals.
- A wrapper function (`preprocess_impedance`) accepts either a file path or a `DataFrame`, so it can be used directly from the Streamlit interface.

> Smoothing removes the points at the ends of the frequency range, and the real-axis intercepts depend directly on those points. Model-free feature extraction is therefore performed on the **unsmoothed data**.

### 3.2 Simulation (`simulation/`)

Generation of synthetic impedances for basic elements and circuits, with optional Gaussian noise. These reference datasets are used to validate the analysis pipeline: a fit performed on simulated data should recover the original parameters.

### 3.3 Circuit models (`models/equivalent_circuits.py`)

Each model is built as `Z(f, *parameters)` returning a complex vector: resistor, capacitor, series RC, parallel RC, simplified Randles. This single signature allows any model to be fitted with the same routine.

### 3.4 Parameter fitting (`analysis/fitting.py`)

SciPy cannot directly fit complex-valued functions, so the real and imaginary parts are **concatenated into a single real vector**:

```math
\mathbf{y} = \begin{bmatrix} \mathrm{Re}(Z) \\ \mathrm{Im}(Z) \end{bmatrix}
```

The fit uses `scipy.optimize.curve_fit` with two design choices motivated by the physics of the parameters:

- **Strictly positive bounds** (lower bound $10^{-15}$): $R$ and $C$ cannot be negative, and a value of exactly zero would cause a division by zero in models such as $1/R_{ct}$. Providing bounds switches SciPy to the *Trust Region Reflective* algorithm.
- **`x_scale="jac"`**: parameters live on very different scales ($R \sim 10$–$10^3\,\Omega$, $C \sim 10^{-6}\,\mathrm{F}$); automatic Jacobian-based scaling improves convergence.

### 3.5 Quality metrics (`analysis/metrics.py`)

For complex residuals $r_i = Z_i^{data} - Z_i^{model}$:

$$
\text{RMSE} = \sqrt{\frac{1}{N}\sum_i |r_i|^2}, \qquad
\text{MAE} = \frac{1}{N}\sum_i |r_i|, \qquad
\chi^2 = \sum_i \left(\frac{|r_i|}{\sigma}\right)^2
$$

By default $\sigma = 1$: the reported $\chi^2$ is a relative indicator, not a statistical test, until the actual measurement noise is estimated.

### 3.6 Model-free features (`analysis/features.py`)

Direct readings from the spectrum: $R_{high}$ (high-frequency end), $R_{low}$ (low-frequency end), their difference, and the frequency $f_{apex}$ of the maximum of $-Z''$. The extraction raises reliability flags when these values should not be taken at face value (spectrum not reaching the real axis, no low-frequency plateau, apex at the edge of the measured range).

### 3.7 Electrochemical interpretation (`analysis/interpretation.py`)

Each derived quantity is returned as an `InterpretedResult` object holding its **value**, **unit**, **formula**, a list of **assumptions** and **notes**. Only quantities whose inputs are provided are computed; **nothing is assumed by default**.

| Quantity | Formula | Required inputs |
|---|---|---|
| Time constant | $\tau = R_{ct}\,C_{dl}$ | fit only |
| Characteristic frequency | $f_c = \dfrac{1}{2\pi\tau}$ | fit only |
| Specific capacitance | $C_{spec} = \dfrac{C_{dl}}{A}$ | electrode area |
| Exchange current density | $j_0 = \dfrac{RT}{nF\,R_{ct}\,A}$ | area, $n$, $T$ |
| Electrolyte conductivity | $\kappa = \dfrac{K}{R_s}, \; K = \dfrac{L}{A}$ | cell geometry |

Comparing $f_c$ (from the fit) with $f_{apex}$ (measured) provides an **internal consistency check**: a large mismatch indicates that the single-semicircle model describes the data poorly.

### 3.8 Interactive application (`app/streamlit_app.py`)

A Streamlit interface that ties everything together: CSV upload, model selection, initial guesses, Nyquist/Bode plots (data, then data vs fit), model-free features, fit results, and an interpretation panel with expandable formulas and assumptions.

---

## 4. Repository structure

```
eis-analysis-platform/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                  # raw measurements
│   ├── processed/            # cleaned data
│   └── simulated/            # synthetic validation data
├── docs/                     # methodology, fundamentals, equivalent circuits
├── notebooks/
│   ├── 01_eis_fundamentals.ipynb
│   ├── 02_resistor_simulation.ipynb
│   ├── 03_capacitor_simulation.ipynb
│   ├── 04_rc_simulation.ipynb
│   ├── 05_randles_simulation.ipynb
│   ├── 06_visualisation.ipynb
│   └── 07_circuit_fitting.ipynb
├── src/
│   ├── simulation/           # resistor, capacitor, rc_circuit, randles
│   ├── models/               # equivalent_circuits.py
│   ├── processing/           # preprocessing.py
│   ├── visualization/        # nyquist.py, bode.py
│   └── analysis/             # fitting, features, interpretation, metrics
├── results/
│   ├── figures/
│   └── reports/
└── app/
    └── streamlit_app.py
```

The notebooks follow a pedagogical progression, from basic concepts (Ohm's law, sinusoidal signals, complex numbers, impedance) to circuit fitting. Reusable code lives in `src/`; the notebooks import it.

---

## 5. Installation and usage

```bash
git clone https://github.com/<username>/eis-analysis-platform.git
cd eis-analysis-platform

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Main dependencies: `numpy`, `pandas`, `scipy`, `matplotlib`, `streamlit`.

**Run the application:**

```bash
streamlit run app/streamlit_app.py
```

**Typical workflow:**

1. Upload an impedance CSV file.
2. Inspect the Nyquist and Bode plots and the model-free features.
3. Choose an equivalent circuit and enter consistent initial values (guided by $R_{high}$, $R_{low}-R_{high}$ and $f_{apex}$).
4. Run the fit, assess RMSE and $\chi^2$, and compare data with the model.
5. For the Randles model, enter the area, temperature, number of electrons and optionally the cell geometry to obtain the electrochemical quantities.

---

## 6. Data format

CSV file with the following columns:

| Column | Content | Unit |
|---|---|---|
| `frequency` | measurement frequency | Hz |
| `real` | real part $Z'$ | Ω |
| `imag` | imaginary part $Z''$ (negative for capacitive behaviour) | Ω |

```csv
frequency,real,imag
100000,10.2,-0.8
10000,12.5,-7.9
1000,60.1,-48.3
```

Nyquist plots show $Z'$ against $-Z''$, following the usual convention.

---

## 7. Expected results

**Validation on simulated data.** For a known circuit and low noise, the fit should recover the original parameters with a small relative error, and $f_c$ should coincide with $f_{apex}$.

**On experimental data.** For each analysed spectrum, the platform produces:

- Nyquist and Bode plots of the data and the fit;
- fitted parameters $(R_s, R_{ct}, C_{dl})$ with their covariance matrix;
- quality metrics (RMSE, $\chi^2$);
- derived quantities ($\tau$, $f_c$, $C_{spec}$, $j_0$, $\kappa$) when the required inputs are provided;
- for each of these quantities, the explicit list of assumptions under which it is valid.

**Methodological outcome.** A concrete demonstration of the difference between a *fitted* parameter, a *measured* quantity and an *interpreted* quantity, and of how uncertainty and assumptions propagate from one level to the next.

---

## 8. Limitations and assumptions

These limitations are deliberate and documented in the code; they are part of the scientific message of the project.

- **Ambiguity of equivalent circuits.** Several circuits can reproduce the same spectrum. A good fit does not prove that the circuit reflects physical reality.
- **Ideal capacitor.** The simplified Randles model assumes an ideal $C_{dl}$. Real interfaces (roughness, porosity) often behave as a constant-phase element (CPE), not yet implemented.
- **No diffusion.** The Warburg impedance is not modelled; if diffusion contributes to the spectrum, $R_{ct}$ is biased.
- **$j_0$ under strict conditions.** The relation $j_0 = RT/(nFR_{ct}A)$ assumes equilibrium, a linear perturbation, a simple reaction and a known electroactive area. If $R_{ct}$ contains other resistive contributions, $j_0$ is underestimated.
- **Conductivity.** $R_s$ is assumed to be purely electrolytic (excluding contacts, wires and reference-electrode junction), with uniform current distribution.
- **Plausibility range for $C_{spec}$.** The 5–100 µF/cm² warning is a rule of thumb for flat electrodes in aqueous media: a hint, not a proof.
- **Relative $\chi^2$.** Without an estimate of $\sigma$ or weighting, $\chi^2$ is not a hypothesis test.
- **Data consistency validation.** No Kramers-Kronig-type check is implemented yet.

---

## 9. Skills developed

### Theoretical

- Complex impedance, Nyquist and Bode representations, frequency response of first-order systems.
- Equivalent circuits and the link between time constants and physical processes.
- Interfacial electrochemistry: double layer, charge transfer, linearised Butler-Volmer kinetics, electrolyte conductivity.
- System identification: parametric fitting, identifiability, sensitivity to initial conditions.
- Error statistics: complex residuals, RMSE, $\chi^2$, parameter covariance.
- Scientific critical thinking: distinguishing measurement, model and interpretation.

### Technical

- **Scientific Python**: NumPy (complex vectorised computation), pandas (data cleaning), SciPy (`curve_fit`, bounds, TRF/LM algorithms), Matplotlib.
- **Non-linear optimisation**: reformulating a complex-valued problem as a real one, parameter scaling, positivity constraints.
- **Software engineering**: modular architecture (`simulation / models / processing / analysis / visualization`), uniform function signatures, `dataclasses`, separation of concerns.
- **Application development**: Streamlit, session-state management, detection of stale results.
- **Reproducibility**: pedagogical notebooks, simulated reference data, assumptions explicitly attached to each result.

---

## 10. Future work

- Constant-phase element (CPE): $Z_{CPE} = \dfrac{1}{Q(j\omega)^\alpha}$.
- Warburg impedance and full Randles circuits with diffusion.
- Data validation with the Kramers-Kronig relations.
- Weighted fitting and estimation of measurement noise (non-unit $\sigma$).
- Confidence intervals on derived quantities from the parameter covariance.
- Automatic initialisation of parameters from model-free features.
- Automated comparison of several circuits (AIC/BIC information criteria).
- Unit tests on simulated data (recover the original parameters).
- Applied example on a real device (sensor, biosensor, modified electrode).

---

## 11. References

- Lasia, A. *Electrochemical Impedance Spectroscopy and its Applications*. Springer, 2014.
- Orazem, M. E., Tribollet, B. *Electrochemical Impedance Spectroscopy*. Wiley, 2nd ed., 2017.
- Bard, A. J., Faulkner, L. R., White, H. S. *Electrochemical Methods: Fundamentals and Applications*. Wiley, 3rd ed., 2022.
- Barsoukov, E., Macdonald, J. R. (eds.). *Impedance Spectroscopy: Theory, Experiment, and Applications*. Wiley, 3rd ed., 2018.
- Virtanen, P. et al. "SciPy 1.0: fundamental algorithms for scientific computing in Python". *Nature Methods*, 17, 261–272, 2020.

---

## 12. Author and license

**Author:** *Kirolos Morcos* · *ENSISA / Electronics, Electrical Energy and Automation (EEA)*

**License:** MIT (see `LICENSE`).

*Academic and educational project. The electrochemical interpretations provided are conditional on the stated assumptions and do not replace an expert analysis of the system under study.*
