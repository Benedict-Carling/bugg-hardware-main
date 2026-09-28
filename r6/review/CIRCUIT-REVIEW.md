# Circuit review — Bugg r6 prototype

*This review was an AI-assisted review pass, separate from the passes that produced the design; it is not an independent human engineering review.*

28 September 2026. Reviewed actual r6 XML connectivity, component definitions, firmware, and manufacturer documents. No hardware measurements; PCB routing is owned separately. A completed PCB/DRC does not establish analogue performance.

## Must-fix findings resolved in source

**Modem shutdown ordering.** The original helper isolated host interfaces only after observing VGPIO off for 100 ms. Revision 16 Figure 4-2 note (a) requires isolation before VGPIO falls; section 4.24.5 also requires it before VBATT removal. `shutdown()` now sends the command, promptly isolates interfaces, waits for the fresh latch/VGPIO handshake, then removes supply. The callback must return after transmission, not after USB disappearance/shutdown. Host scheduling and actual electrical isolation still require validation. Added timing-order and callback-failure tests; all **22 firmware tests pass**. [Manufacturer specification, pp. 68, 104](https://www.bipom.com/documents/GetWireless/41113440%20RC76xx%20Product%20Technical%20Specification%20r16.pdf)

**Inherited wake input did not suit an RC waveform.** U14 was a TI SN74LVC1G07 with a 10 ns/V maximum input transition time at 3.3 V, driven by a nominal 51 ms RC. Its ±5 µA input-leakage limit also permits a 2.55 V error across R30=510 kΩ. These were inherited weaknesses, not newly measured failures. [Original buffer specification, §§5.3–5.5](https://www.ti.com/lit/ds/symlink/sn74lvc1g07.pdf)

The schematic now specifies U14 **SN74LVC1G37DCKR**, R29 **100 kΩ**, R30 **47 kΩ**, C36 **1 µF**. U14 retains the exact five-pin DCK footprint/pinout, noninverting behavior and open-drain output. Its Schmitt input supports slow edges; the current datasheet table allows 100 ms/V. R30's leakage error becomes 0.235 V; R29's RTC-output leakage error becomes 0.05 V. Nominal RC remains similar: **47 ms versus 51 ms**. PCB values, libraries and BOM were subsequently synchronized; the final source-bound checks pass. [Replacement buffer specification](https://www.ti.com/lit/gpn/SN74LVC1G37)

C36 is **GRM155R61C105KA12D**, 1 µF ±10%, 16 V, X5R, 0402, rated −55…85 °C. Its exact effective capacitance under bias is not guaranteed by the nominal value. [Murata component specifications](https://www.murata.com/en-global/products/productdetail?partno=GRM155R61C105KA12%23)

The CM4 requires GLOBAL_EN low for more than 1 ms. Illustrative 3.3 V RC calculations give about 31 ms for a 1.8 V rising threshold, and about 4.6 ms using 0.4 µF, a 1.3 V threshold and adverse leakage/initial-voltage assumptions. These are scenarios, not a guaranteed pulse-width specification. On alarm release, the open-drain RTC output rises through R29; R29/R30 limit the nominal positive input excursion to about 0.93 V rather than a full 3.3 V step. Validate cold/hot wake, startup, alarm-clear/re-arm, capacitor bias, and GLOBAL_EN loading. [CM4 datasheet, §2.13 and pin 99](https://datasheets.raspberrypi.com/cm4/cm4-datasheet.pdf)

## Prototype validation, not reasons to invent a performance claim

**ADC filtering:** 200 Ω/4.7 nF yields the documented ideal transfer function. The 11.08 µs full-step calculation is not a SAR settling proof. Confirm CNV/acquisition timing and ADC configuration in the actual audio bridge; high-Z mode is disabled by default. Driver stability, kickback and THD remain unresolved. Restrict this population to the stated 44.1/48 kHz experiment; retain 180 pF as the comparison population. No extra SNR or self-noise claim is justified yet. [AD4005 datasheet, §§Driver Amplifier Choice, High-Z Mode, Long Acquisition Phase](https://www.analog.com/media/en/technical-documentation/data-sheets/AD4001-4005.pdf)

**Bias filtering:** XML confirms R104=100 Ω and Q25 upstream of that resistor. The 34 dB nominal / 26 dB assumed-derated 8 kHz ripple figures are credible ideal supply-transfer calculations. The higher-current microphone branch bypasses the filter. Check capsule headroom, C83 effective capacitance and startup; this does not filter downstream interference or prove a quieter capsule/recording.

**RTC power and backup:** The 3.3 V regulator is compatible with the nominal 5.4 V system rail. Verify rail overshoot remains within the regulator's 6 V recommended maximum. The existing CR1220 is retained; provisioning disables charging and enables backup switching while preserving factory trim. Do not call the new RTC a new backup-timekeeping capability. Its ±2.5 ppm headline excludes aging and other unbudgeted board effects. [TPS7A02](https://www.ti.com/lit/ds/symlink/tps7a02.pdf), [RV-3032 application manual](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3032-C7_App-Manual.pdf)

**Telemetry power sequencing:** Always-on ADS1115 supply avoids tying its dividers to the CM4's switched 3.3 V rail. It does not prove zero injection during startup, brownout or main-rail failure. ADS analog inputs must remain within GND−0.3 V to VDD+0.3 V; the ±4.096 V PGA setting does not relax this. Series dividers limit current, but scope startup/fault states and reject measurements until the rail is valid. Divider loading/ADC input impedance and tolerance require calibration; resolution is not accuracy. [ADS1115 datasheet, §§5.1, 7.3.1](https://www.ti.com/lit/ds/symlink/ads1115.pdf)

**Modem level translation/latch:** Pin 45 VGPIO and pin 152 SAFE_PWR_REMOVE, NPN inversion, Schmitt cleanup, trailing-edge latch and active-low clear are logically consistent. A fresh latch event prevents mistaking VGPIO-off PSM for completed shutdown. The 47 kΩ base resistors draw only tens of µA at nominal 1.8 V; collectors pull roughly 0.33 mA. Verify low/high levels over temperature and modem-output limits, latch startup, brownout, pulse polarity and USB/interface isolation on the actual board. Do not publish a quantified reliability improvement.

## Credible benefit summary

The design offers calculable rejection on two interference paths, tighter specified calendar-clock accuracy, four-rail voltage visibility, and captured modem shutdown confirmation. The wake buffer change also resolves a datasheet mismatch in the retained RC path. No evidence yet supports a dB(A) self-noise reduction, battery-life increase, improved ultrasonic fidelity, or measured field reliability.
