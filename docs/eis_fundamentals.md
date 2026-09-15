# EIS Fundamentals  

This document introduces the essential electrical and mathematical concepts required before analysing impedance data or building equivalent circuits.

---

## 1. What is Electrochemical Impedance?

Electrochemical Impedance Spectroscopy (EIS) measures how a system responds to a small AC perturbation across a range of frequencies.  
The result is a complex impedance:



$$
Z(\omega) = Z'(\omega) + j Z''(\omega)
$$



where:

- $Z'$: real (resistive) part  
- $Z''$: imaginary (reactive) part  

---

## 2. AC Signals

A sinusoidal voltage is defined as:



$$
v(t) = V_0 \sin(\omega t + \phi)
$$



Key quantities:

- **Frequency:** $f$ (Hz)  
- **Angular frequency:** $\omega = 2\pi f$  
- **Period:** $T = 1/f$  
- **Phase shift:** $\phi$

---

## 3. Complex Numbers

EIS uses complex arithmetic:



$$
z = a + jb
$$



Magnitude:



$$
|z| = \sqrt{a^2 + b^2}
$$



Phase:



$$
\varphi = \arctan\left(\frac{b}{a}\right)
$$



---

## 4. Impedance

Impedance generalises resistance for AC signals:



$$
Z = R + jX
$$



where:

- $R$: resistive part  
- $X$: reactive part  

Impedance depends on frequency, unlike DC resistance.

---

## 5. Ideal Components

### 5.1 Resistor  


$$
Z_R = R
$$



- Purely real  
- Independent of frequency  
- Voltage and current in phase  

### 5.2 Capacitor  


$$
Z_C = \frac{1}{j\omega C}
$$



- Purely imaginary  
- Magnitude decreases with frequency  
- Current leads voltage by $90^\circ$

---

## 6. Series RC Circuit



$$
Z_{RC} = R + \frac{1}{j\omega C}
$$



Real part:



$$
\Re(Z_{RC}) = R
$$



Imaginary part:



$$
\Im(Z_{RC}) = -\frac{1}{\omega C}
$$



This circuit produces the characteristic semicircle in Nyquist plots.

---

## 7. Nyquist and Bode Plots

### Nyquist  
Plots $-\Im(Z)$ vs $\Re(Z)$.  
Shows geometric features (semicircles, straight lines).

### Bode  
Plots magnitude and phase vs frequency.  
Shows frequency-dependent behaviour.

---

## 8. Why These Fundamentals Matter

These concepts form the mathematical backbone of:

- Synthetic dataset generation  
- Equivalent circuit modelling  
- Parameter fitting  
- Interpretation of electrochemical behaviour
