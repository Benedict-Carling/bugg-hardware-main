# Bugg r6 design review

Date: 28 September 2026. Design status: fully routed and verified for prototype review. Hardware status: unbuilt and unmeasured.

## Scope and provenance

This is a revision of the public r5 main board, not a replacement architecture or an official Bugg revision. The original CM4, RC7620 modem, microphone connectors, professional analogue preamplifier, microphone power modes, AD4005 converter and digital audio format are retained. New circuits address microphone supply interference, ADC input bandwidth, timekeeping, supply visibility and modem shutdown confirmation. A button and nine test points added during development were removed again; the pre-existing r5 test points remain.

The unmodified r5 design is `r5/src` in this repository. Source: [Bugg main-board repository](https://github.com/bugg-resources/bugg-hardware-main), commit `e71fd5740865aec2923b8e5c67f93d5d7822d4b3`. Attribution to the Bugg project and its original hardware authors is retained. This derivative is CC BY-NC-SA 4.0. No permission for commercial reuse is implied.

## Proposed headline improvements

| Change | Defensible headline | Evidence and limit |
|---|---|---|
| Plug-in microphone bias | 34 dB nominal calculated supply-ripple rejection at 8 kHz | 100 Ω / 10 µF; 26 dB if effective capacitance is assumed to be 4 µF. Not measured microphone self-noise. |
| ADC input RC | Approximately 18 dB more rejection at 1.38 MHz; 0.06 dB loss at 20 kHz | Ideal passive model; 44.1/48 kHz prototype population, pending ADC/driver validation. |
| Calendar clock | 2× tighter initial specified timekeeping tolerance over −40 to +85 °C | ±2.5 vs ±5 ppm; approximately ±0.22 vs ±0.43 seconds/day, excluding aging and board effects. Not the audio sample clock. |
| RTC wake signal | Schmitt input and reduced leakage sensitivity in the original buffer footprint | Slow RC edge is accepted by the replacement input; pulse width and wake behavior remain unmeasured. |
| Supply telemetry | Four newly monitored voltage rails | Input, system, modem and USB; aids remote diagnosis. No current sensor or state-of-charge estimate. |
| Modem shutdown | Hardware captures a short safe-removal pulse and firmware checks VGPIO too | Avoids relying on Linux polling to catch the pulse. No measured field-reliability percentage. |
| Mechanical compatibility | Original outline and connector/mounting positions retained | Compare actual CAD against r5; physical enclosure/assembly fit remains untested. |

[Detailed audio interpretation](AUDIO-EXPLAINED.md), [headline fact check](HEADLINE-FACT-CHECK.md) and [machine-readable calculations](calculations.json) distinguish electrical filtering from recorded noise.

## Circuit review

**Microphone front end.** Retain THAT1580/THAT5173 and LM4562, gain range and input impedance. R51/R52 remain 1.2 kΩ: increasing them merely to reduce loading risks more bias-current offset at high gain. R104 is 100 Ω; Q25's source is moved to the upstream LDO output so P3V3 current bypasses the plug-in-power filter. R84/R85 remain 10 kΩ. C83's effective capacitance and microphone current are unknown; check headroom and settling with the intended microphone. The internal digital microphone path is unaffected.

**ADC/reference.** C75/C76 are 4.7 nF C0G 0402 (Murata GRM1555C1H472JE01D); the 200 Ω resistors and AD4005 remain. The 169 kHz pole is an interference filter, not a complete 48 kHz audio anti-alias filter. Retain the original 180 pF option for controlled comparison or separately qualified high-rate builds. ADC kickback, actual acquisition timing and LM4562 stability are not established by the ideal RC calculation. The MAX6105 reference and associated headroom requirements remain unchanged.

**Power conversion.** Retain the original converters and input protection. The TPS65130 was already configured for forced PWM, so no burst-mode fix is claimed. Its switching frequency is a plausible interference source, not a proven diagnosis of the whistle. The original system rail is nominally about 5.4 V despite its +5V net name. USB-only operation can still limit analogue reference headroom; telemetry makes voltage observable but does not correct undervoltage. No whole-board power reduction is claimed: CM4 remains the dominant load, and monitoring adds consumption.

**Clock and wake.** Replace DS3231M with RV-3032-C7 and add a 3.3 V always-on TPS7A02 regulator. Retain the CR1220 holder and GLOBAL_EN wake-pulse function, operating its logic from the new rail. The RTC's ±2.5 ppm is an initial calibrated specification; its manual separately lists up to ±3 ppm first-year crystal aging at the stated conditions, so sustained 2× field accuracy is not established.

**Wake signal.** U14 becomes SN74LVC1G37DCKR in the same footprint and pinout: its Schmitt input accepts the slow RC edge while its open-drain output preserves GLOBAL_EN behavior. R29 becomes 100 kΩ, R30 47 kΩ and C36 1 µF. Lower resistance reduces leakage sensitivity; the nominal timing product stays similar (47 ms versus 51 ms), but this is not a guaranteed pulse width. Confirm wake, startup and alarm clear/re-arm across temperature and effective capacitance. Backup charging is disabled. RV-3032 EEPROM needs initial configuration; the included routine preserves factory calibration and avoids repeated EEPROM writes. Calendar wake requires software integration because this circuit does not supply a CM4 interrupt to the standard Linux RTC driver. r5 already had battery-backed time and wake; these are not new capabilities.

**Modem.** Retain the RC7620, supply switch and original enable GPIO. Bring VGPIO and SAFE_PWR_REMOVE through transistor level translation, Schmitt buffers and a flip-flop latch to an I2C expander. The falling end of the safe pulse becomes a rising latch clock. Firmware clears and arms the latch before AT!POWERDOWN, promptly isolates host interfaces after transmitting the command, then requires the new latch event and VGPIO absent for 100 ms before removing power. Isolation must be established before VGPIO falls, not merely before supply removal. The command callback must not wait for USB disappearance or shutdown completion. Linux call order does not establish the electrical deadline; validate actual interface timing on hardware. On timeout or I2C failure it keeps power applied and reports failure. Existing buggd already issues AT!POWERDOWN; this design adds confirmation, not the command itself. Actual timings need waveform validation.

**Voltage telemetry.** ADS1115 at 0x48 is supplied by the always-on rail instead of the CM4's switched rail. This avoids that particular power-off mismatch, but startup and brownout input-injection limits still require checking; the ±4.096 V PGA range does not permit inputs above VDD + 0.3 V. Four 0.1% dividers scale rails by 16, 3, 2 and 3. At ±4.096 V range, nominal rail code increments are 2, 0.375, 0.25 and 0.375 mV. Resolution is not accuracy. The design has no current shunt, charger, battery fuel gauge or solar controller.

**Interfaces and layout.** Preserve original connector coordinates, mounting features, modem and CM4 interfaces, six-layer stack and thickness. Preserve the original USB pair geometry. Preserve original RF paths and supply paths where unaffected by the new circuits. The upstream NT1 inner-only SMD ground tie is changed to plated, tented pads connected by its existing inner-layer strap to address its KiCad padstack errors. That local ground transition still merits assembled-board review.

**Software.** Included support code covers voltage conversion, safe modem shutdown, RTC configuration, time read/write and calendar wake. It is an integration module, not a tested Bugg OS image. The latest run passes 22 unit tests, including host-interface isolation order and callback-failure handling. No software has been exercised on this unbuilt hardware. See [firmware README](../firmware/README.md).

## Validation record

Final native KiCad checks passed: **0 DRC errors, 0 unconnected items, 0 schematic/PCB parity issues and 0 ERC errors**. ERC retains 10 reviewed label-alias warnings (eight multiple-name aliases and two local/global label-name warnings); the actual netlist and 1,826 PCB pad-net comparisons agree. All 37 fixed interfaces and the outline match r5, as do the six copper layers, 1.6 mm thickness, original USB and differential microphone-input copper. The 59 original test points remain; no button or test points were added. There are 493 footprints and 41 BOM changes (33 added parts and eight changed parts).

All **22 firmware unit tests pass**. Ideal passive RC calculations also agree with the separate ngspice check; neither is a measurement of recording noise. Front/back PCB plots and schematic SVGs were refreshed from the completed CAD.

The [circuit review](CIRCUIT-REVIEW.md) led to corrected modem interface-isolation order and the Schmitt wake buffer. The [mechanical/layout review](MECHANICAL-REVIEW.md) led to closer bypass ground vias, explicit ground-pad connections and C144's back-side placement: its routed supply connection is now 1.70 mm instead of 10.27 mm (horizontal copper only). The sole accepted added-part courtyard margin overlap is C144 beside original bare test pad T9; their modeled component-body-to-test-pad copper gap is 0.55 mm, with no component-body collision. No original test pad was moved.

Reproduce the checks from `r6/`: `design/verify_board.py` (KiCad 10 Python) compares the board against `r5/src`; `design/calculations.py` and `design/bom.py` regenerate the calculations and BOM delta from the netlists; `firmware/` tests run with `python3 -m unittest discover -p 'test_*.py'`. The verified board SHA-256 is `197e3304add190f5de6a119007c67d00aedcd17ea45b32a330c22ef7548d9039`.

The design remains unbuilt and unmeasured. Prototype validation must establish ADC settling/stability/distortion, actual microphone noise, wake and modem timing, power sequencing, and enclosure/assembly fit. No measured self-noise reduction, battery-life gain or production readiness is claimed.

## Primary references

- [Bugg audio documentation](https://docs.bugg.xyz/audio/) and [r5 errata](https://github.com/bugg-resources/bugg-notes/blob/main/Bugg%20r5%20Errata.md).
- [AD4005 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/AD4001-4005.pdf), especially RC filter, driver and acquisition sections.
- [DS3231M datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/DS3231M.pdf) and [RV-3032 application manual](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3032-C7_App-Manual.pdf).
- [TPS7A02](https://www.ti.com/lit/ds/symlink/tps7a02.pdf), [ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf), [TCA9536](https://www.ti.com/lit/ds/symlink/tca9536.pdf), [SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf), [SN74LVC2G17](https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf).
- [RC76xx manufacturer specification portal](https://source.sierrawireless.com/resources/airprime/hardware_specs_user_guides/rc76xx---product-technical-specification). The manufacturer's Revision 16 document used for pin/timing review is archived from [this distributor mirror](https://www.bipom.com/documents/GetWireless/41113440%20RC76xx%20Product%20Technical%20Specification%20r16.pdf); latest portal revision requires access.
