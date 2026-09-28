# Headline fact check

*This review was an AI-assisted review pass, separate from the passes that produced the design; it is not an independent human engineering review.*

Reviewed 28 September 2026 against the r5 source snapshot, r6 component delta, calculation output, ideal ngspice results, firmware test record and manufacturer RTC specifications. This is an evidence review, not a finding that the PCB is complete or ready to manufacture. No board has been built or measured.

## Claims that the evidence supports

| Proposed claim | Check | Required qualification |
|---|---|---|
| 34 dB nominal microphone-bias ripple rejection at 8 kHz | Complex voltage-divider calculation gives 34.027 dB for 100 Ω and 10 µF. At 4 µF it gives 26.077 dB. | This is an ideal supply-ripple transfer calculation, not microphone self-noise. The 4 µF case is assumed, not a guaranteed capacitor minimum. |
| About 18 dB more ADC-input rejection at 1.38 MHz | With 200 Ω, 180 pF gives 0.404 dB attenuation and 4.7 nF gives 18.289 dB: a 17.885 dB difference, or 7.84× less interference voltage. | One possible interference path only. A specific Bugg whistle source has not been identified. |
| 0.06 dB ADC-filter loss at 20 kHz | The revised ideal filter gives 0.06018 dB, corresponding to about 0.69% amplitude reduction. | Does not establish distortion, ADC settling or driver stability. The 4.7 nF population is experimental and intended for 44.1/48 kHz evaluation. |
| Twice as tight initial specified calendar-clock tolerance | 2.5 ppm × 86,400 s/day = 0.216 s/day; 5 ppm = 0.432 s/day. Compare both over −40 to +85 °C. | Calendar timing, not audio sample timing. Manufacturer tolerance is not measured board accuracy or a lifetime guarantee. |
| Four newly monitored supply voltages | ADS1115 channels are VIN, system rail, modem rail and USB VBUS. 125 µV/code multiplied by divider ratios 16/3/2/3 gives 2/0.375/0.25/0.375 mV per rail code. | Code resolution is not accuracy. No current, energy, state-of-charge or battery-life result. |
| Hardware capture of the modem safe-removal pulse | The design captures the pulse end in a latch. Support software promptly isolates host I/O after command transmission, then checks a fresh latch event plus VGPIO absent for 100 ms before its power-off callback. Hardware must establish isolation before VGPIO falls. | A designed handshake, not measured field reliability. Existing r5 software already uses AT!POWERDOWN. |
| Same outline and original connector positions | A dedicated verifier compares the actual board to the archived r5 board and 37 original mechanical interfaces. | Final claim requires the verifier against the final board; real enclosure and assembly fit remain untested. Six layers were already used by r5. |

The passive arithmetic was recalculated independently using the complex transfer `H = 1 / (1 + j·2πfRC)`, rather than reusing the calculation script's decibel expression. All headline values agree. Five recorded ngspice cases independently agree with the ideal passive formula within 0.000001 dB. That agreement validates the ideal network calculation, not an ADC or complete recording system model.

R104 changes from 0 Ω to 100 Ω; C83 stays nominally 10 µF. The higher-current P3V3 branch bypasses this resistor. R61/R62 stay 200 Ω; C75/C76 change from 180 pF to 4.7 nF. The audio changes apply to the external analogue microphone path, not the internal digital microphone.

## Calendar accuracy wording

Use **“twice as tight initial specified timekeeping tolerance”**. The RV-3032 application manual separately lists up to ±3 ppm first-year crystal aging at its stated conditions. Thus “twice as accurate in the field” over an extended deployment is not established. The DS3231M already provided battery backup; retaining time with the main supply disconnected is not a new capability. [RV-3032 manual, oscillator parameters §7.3](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3032-C7_App-Manual.pdf), [DS3231M specification, timekeeping characteristics](https://www.analog.com/media/en/technical-documentation/data-sheets/DS3231M.pdf).

## Claims to leave out

Do not describe the board as 34 dB quieter, claim an 18 dB SNR gain, or claim longer recording range. Do not combine the two filter dB numbers: they act on different paths. No whole-board power reduction, battery-life extension or improved shutdown failure rate has been calculated or measured. The RTC change and new monitoring need software integration; this is not a drop-in r5 software image.

The recorded firmware run passed 22 unit tests using simulated buses and signals. It does not establish hardware timing, boot behavior or integration with Bugg OS. The existing CM4 and modem remain; this is a targeted main-board revision, not an improvement to every aspect of the system.
