# What the two audio changes actually mean

These are calculated improvements to two electrical interference paths. They are **not measured improvements to acoustic self-noise, SNR, distortion or detection range**. No suitable raw Bugg external-input self-noise WAV was found during the initial search. PCB inspection is enough to design and calculate filters; it cannot identify which noise source dominates a recording.

## 1. Cleaner plug-in microphone bias

R5 connects the 3.3 V analogue LDO output to the plug-in-power rail through a 0 Ω link, R104. R6 changes that link to 100 Ω and uses the existing C83 (10 µF nominal) to filter ripple. The Q25/P3V3 higher-current microphone-power branch is moved upstream of R104. The plug-in-power branch remains downstream.

At 8 kHz, the ideal unloaded RC response is:

| Effective C83 | Ripple rejection | Ripple voltage reduction |
|---|---:|---:|
| 10 µF nominal | 34.03 dB | 50.3× |
| 6 µF assumed | 29.59 dB | 30.2× |
| 4 µF assumed | 26.08 dB | 20.1× |

For example, 1 mV of incoming 8 kHz ripple becomes about 20 µV with the nominal capacitance. The 4–6 µF values are scenarios for capacitance loss under DC bias, **not a verified minimum or a tolerance guarantee**. Loading, capacitor impedance, layout and other coupling paths change the real response.

This filter is in the **power supply**, not the microphone audio signal. Its approximately 159 Hz nominal corner therefore does not mean it cuts off bird calls above 159 Hz. It smooths the DC supply feeding the microphone. It can reduce whines or buzz caused by that supply, depending on the microphone's supply-to-output coupling. It does not remove microphone capsule hiss, amplifier noise, ground coupling, RF demodulation, or a whistle injected farther down the signal chain. It does not filter the bypassed P3V3 output by the same amount.

Tradeoffs: the extra resistor drops 50 mV at 0.5 mA and 100 mV at 1 mA, consumes a little microphone voltage headroom, and adds nominally 4.6 ms to reach 99% of the supply step. The original 10 kΩ microphone feed resistors are retained. Microphone compatibility and total startup settling still need checking. The resistor's own thermal noise is included in a complete noise budget; this calculation only describes ripple transfer.

## 2. Less high-frequency interference at the ADC input

R6 retains R61/R62 at 200 Ω and increases C75/C76 from 180 pF to 4.7 nF C0G. This lowers the ideal single-pole corner from 4.42 MHz to 169.3 kHz.

| Frequency | R5 attenuation | R6 attenuation | Extra rejection |
|---|---:|---:|---:|
| 8 kHz | <0.001 dB | 0.010 dB | 0.010 dB |
| 20 kHz | <0.001 dB | 0.060 dB | 0.060 dB |
| 80 kHz | 0.001 dB | 0.875 dB | 0.874 dB |
| 1.38 MHz | 0.404 dB | 18.289 dB | 17.885 dB |

At 20 kHz, the revised filter reduces amplitude by approximately 0.7%; its effect is smaller at lower audio frequencies. At 1.38 MHz, it passes about 7.84 times less interference voltage than r5. A possible benefit is reduced audible artifacts from high-frequency power-converter noise reaching the ADC inputs.

Sampling can turn an ultrasonic electrical tone into an audible one. For **48 kHz sampling**, a 1.38 MHz tone folds to 12 kHz and a 1.40 MHz tone folds to 8 kHz. This arithmetic does not establish the source of Bugg's reported 8 kHz whistle. Interference introduced after this filter, into the reference or ground, or in digital timing does not necessarily receive this attenuation. An 8 kHz tone already present in the analogue audio passes almost unchanged.

This is **not a complete audio anti-alias filter**. With a 169 kHz corner it barely attenuates signals near the 24 kHz Nyquist boundary of a 48 kHz recording. It targets much higher-frequency interference. It also does not improve the internal digital microphone's audio path.

The design tradeoff is ADC settling and driver stability. An ideal full-scale RC step takes about 11.08 µs to settle within half of one 16-bit code. That is not a proof of ADC performance: switched-capacitor kickback, acquisition timing, amplifier dynamics and continuous signals require a fuller model and hardware verification. R5's 200 Ω/180 pF combination follows a manufacturer-recommended starting point; changing it is an application-specific bandwidth tradeoff, not evidence that the original design was mistaken. The 4.7 nF population is an experimental 44.1/48 kHz profile. High-rate modes need separate validation; the original 180 pF population remains an alternative for comparison. [Analog Devices AD4005 datasheet, RC filter and driver sections](https://www.analog.com/media/en/technical-documentation/data-sheets/AD4001-4005.pdf)

## Will recordings actually sound better?

Potentially, if one of these interference paths is significant. Less electrical whine would make quiet calls cleaner and reduce false spectral features. Neither change increases microphone sensitivity or restores sounds already lost in the microphone. If capsule or preamplifier hiss dominates, the total noise improvement may be small even with excellent ripple rejection. Overall noise is the combination of multiple sources, not the attenuation of one filter.

The appropriate external claim is: **“Calculated microphone-bias ripple rejection of 34 dB nominal at 8 kHz, plus approximately 18 dB more ADC-input rejection at 1.38 MHz with 0.06 dB calculated attenuation at 20 kHz. Hardware noise and distortion measurements are pending.”**

Do not describe this as “34 dB quieter recordings,” “18 dB better SNR,” or a measured self-noise improvement. A-weighted noise, unweighted spectrum, tonal peaks and distortion should be reported separately when hardware exists, with identical microphones, gain, sample rate, bandwidth and supply/modem states.

Calculations are reproducible with `python3 design/calculations.py` and cross-check actual schematic component values. The response uses `10 log10(1 + (2πfRC)^2)` dB of attenuation.
