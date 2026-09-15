# **Equivalent Circuit Models for EIS**  
*Electrochemical Impedance Spectroscopy Data Analysis Platform — Stage 4 Documentation*

---

## **1. Purpose of This Document**

This page introduces the electrical models used to interpret impedance data in Stage 4 of the project.  
It explains:

- The physical meaning of each circuit element  
- The mathematical impedance expressions  
- How these models relate to Nyquist and Bode plots  
- How they are implemented in `src/models/equivalent_circuits.py`  
- How they are used in `06_circuit_fitting.ipynb`  

This stage corresponds to the roadmap section:

> “Move from data visualisation to physical and electrical interpretation using equivalent circuit models.”  


---

## **2. Why Equivalent Circuits?**

EIS measurements capture how a system responds to sinusoidal excitation across frequencies.  
Equivalent circuits allow us to **map physical electrochemical phenomena** to **electrical components**.

From the roadmap:

> “Understand how physical and electrochemical phenomena can be approximated using electrical components such as Rs, Rct and Cdl.”  


These models help interpret:

- Solution resistance  
- Charge transfer kinetics  
- Double‑layer capacitance  
- Diffusion effects (in advanced models)

---

## **3. Basic Components**

All component models are implemented in `src/models/equivalent_circuits.py`.

### **3.1 Resistor (R)**  
Impedance:  
$$
Z_R = R
$$

From the fundamentals notebook:

> “For an ideal resistor, $R$ is constant and does not depend on frequency.”  


In code:

```python
def Z_resistor(R):
    def model(f):
        return R * np.ones_like(f, dtype=complex)
    return model
```

---

### **3.2 Capacitor (C)**  
Impedance:  
$$
Z_C = \frac{1}{j\omega C}
$$

From the fundamentals notebook:

> “This simple RC circuit is a basic model used in EIS to represent charge transfer resistance and double‑layer capacitance.”  


In code:

```python
def Z_capacitor(C):
    def model(f):
        omega = 2 * np.pi * f
        return 1 / (1j * omega * C)
    return model
```

---

## **4. RC Circuits**

### **4.1 Series RC Circuit**  
Impedance:  
$$
Z_{RC} = R + \frac{1}{j\omega C}
$$

This produces a **semicircle** in the Nyquist plot.  
The real part is constant (R), while the imaginary part decreases with frequency.

In code:

```python
def Z_rc_series(R, C):
    def model(f):
        omega = 2 * np.pi * f
        Zc = 1 / (1j * omega * C)
        return R + Zc
    return model
```

---

### **4.2 Parallel RC Circuit**  
Impedance:  
$$
Z_{RC} = \frac{1}{\frac{1}{R} + j\omega C}
$$

This model is often used to represent **charge transfer resistance in parallel with double‑layer capacitance**.

In code:

```python
def Z_rc_parallel(R, C):
    def model(f):
        omega = 2 * np.pi * f
        Y = (1 / R) + (1j * omega * C)
        return 1 / Y
    return model
```

---

## **5. Randles Circuit (Simplified)**

The Randles circuit is the most common electrochemical model:

- $R_s$: solution resistance  
- $R_{ct}$: charge transfer resistance  
- $C_{dl}$: double‑layer capacitance  

Impedance:  
$$
Z = R_s + \frac{1}{\frac{1}{R_{ct}} + j\omega C_{dl}}
$$

From the roadmap:

> “Understand the simplified Randles circuit.”  


In code:

```python
def Z_randles(Rs, Rct, Cdl):
    def model(f):
        omega = 2 * np.pi * f
        Y_parallel = (1 / Rct) + (1j * omega * Cdl)
        Z_parallel = 1 / Y_parallel
        return Rs + Z_parallel
    return model
```

---

## **6. Using the Models in the Project**

### **6.1 Where the models live**
- `src/models/equivalent_circuits.py`

### **6.2 Where they are used**
- `notebooks/06_circuit_fitting.ipynb`

This notebook:

- Loads a dataset  
- Selects a model  
- Computes theoretical impedance  
- Compares Nyquist and Bode plots  
- Computes residuals (RMSE)  

### **6.3 Example usage**

```python
from models.equivalent_circuits import Z_rc_series, evaluate_model

model = Z_rc_series(R=100, C=1e-6)
Z_model = evaluate_model(model, frequencies)
```

---

## **7. Physical Interpretation Guide**

### **Nyquist Plot**
- Semicircle → RC behavior  
- Diameter → charge transfer resistance  
- High‑frequency intercept → solution resistance  
- Low‑frequency tail → diffusion (not included in Stage 4)

### **Bode Magnitude**
- Capacitive systems show decreasing $|Z|$ with frequency  
- Resistive systems show flat magnitude  

### **Bode Phase**
- Capacitor → $−90°$  
- Resistor → $0°$  
- RC → transition between $0°$ and $−90°$

---

## **8. Summary**

Stage 4 transforms the platform from a visualisation tool into a **scientific modelling engine**:

- You now simulate physical behavior  
- Compare theory vs data  
- Interpret electrochemical phenomena  
- Prepare for Stage 5 (parameter fitting)

From the roadmap:

> “Required output: Scientific Modelling Platform: ability to simulate equivalent circuits and compare theoretical impedance behaviour with data.”  