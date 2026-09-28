# r6 software integration

This board retains the CM4, RC7620, original GPIO assignments, SPI gain control, microphone modes, I2S slot multiplexer and AD4005 data format. It is **not a drop-in r5 software image**: the RTC is different and the new monitoring circuits need support. No code here has been run on r6 hardware.

`r6_support.py` provides an smbus2-compatible four-rail monitor and modem shutdown guard. `test_r6_support.py` exercises success, missing/stale handshake, I2C failure, reset, timeout, input bounce and voltage scaling. Use one process/lock to own I2C transactions. Do not bind a kernel GPIO/ADC driver to an address also used by these classes.

I2C address map:

| Device | Address | Usage |
|---|---:|---|
| RV-3032-C7 | 0x51 | Replaces DS3231M at 0x68 |
| ADS1115 | 0x48 | VIN, +5V, +3V7, USB VBUS |
| TCA9536 | 0x41 | Modem VGPIO, safe-pulse latch, latch arm, spare |
| Existing LED PCF8574 | 0x23 | Unchanged |
| Existing microphone bridge | Inspect the original microphone-board image | Unchanged |

## Modem integration

In `buggd/drivers/modem.py`, keep `AT!POWERDOWN`. Immediately before it, call `guard.arm()`. Finish transmitting the command, promptly disable connected host interfaces (high impedance or LOW), then call `guard.wait_ready()`. Only after the fresh safe-pulse event and stable VGPIO-off confirmation should the existing GPIO7 modem supply enable be deasserted. The convenience `guard.shutdown()` takes callbacks for these operations. The RC76xx Revision 16 Figure 4-2 note (a) requires interface isolation **before VGPIO switches off**, which is earlier than removing the supply.

The command callback must return promptly after transmission. Do not reuse a callback that waits for USB disappearance, VGPIO loss or shutdown completion; that delays isolation too far. If an immediate AT acknowledgement is consumed, its timeout must still allow isolation before VGPIO falls. The isolation callback must return only after the electrical state is established. Actual host/USB handling and this timing need oscilloscope verification; Python call order alone cannot guarantee a deadline on Linux.

On a missing handshake or I2C error, log the fault and keep the supply enabled. If a deployment needs forced recovery from a crashed modem, make that a separate explicit recovery path with a persistent event log; it is not a successful graceful shutdown. VGPIO falling by itself is insufficient. The latch captures the end of the short SAFE_PWR_REMOVE pulse, so normal Linux scheduling does not need to sample a 13 ms pulse live.

The latch input passes through an NPN translator and a Schmitt buffer. P0=1 means VGPIO absent; P1=1 means a safe pulse ended since the latch was armed; P2=1 arms the latch. P2 has an external 10k pulldown for a defined reset state. Set TCA9536 special register 0x50 to 0x40 to disable its weak pullups.

## RTC bring-up

The new RTC needs `rtc-rv3032` if using the Linux RTC framework. Remove the DS3231 overlay. A new device must have backup switching enabled: its factory default is disabled. Keep the charger **disabled** for the primary CR1220. Target EEPROM PMU register C0h is **0x50** (NCLKE=1, BSM=01, TCM=00), retaining any intentional TCR bits if present. Do not reuse an RV-3032 configuration written for a rechargeable backup supercapacitor.

Use `rtc_config.py` for one-time bench provisioning with the RTC kernel driver unbound. It writes only PMU EEPROM, leaves the factory temperature/offset registers alone and verifies the result. Afterwards bind the normal kernel driver. On a kernel exposing RTC backup-switch parameters, direct switching can also be selected through its RTC parameter interface, but that alone does not validate the charger or CLKOUT settings.

The retained alarm-to-GLOBAL_EN circuit is a **power wake/reset pulse**, not a CM4 GPIO interrupt. Mainline `rtc-rv3032` disables its normal alarm feature when no IRQ is supplied. Do not assume `rtcwake` works unchanged. For timed shutdown, the included `RTC3032.alarm_at()` supplies a calendar wake through an exclusive I2C owner: it rounds up to a minute, requires 2 minutes to 27 days of lead time, and uses the retained GLOBAL_EN pulse circuit. Call `clear_wake()` early at the next boot. The class also supplies UTC clock read/set operations. Use this userspace owner with the kernel RTC driver unbound, or port the transactions into the kernel driver; do not run two owners. Test the physical wake before deployment. Normal timekeeping does not depend on the power-wake integration.

The r6 wake buffer is now SN74LVC1G37DCKR: a Schmitt input accepts the slow RC edge, while its open-drain output preserves GLOBAL_EN behavior. R29=100k, R30=47k and C36=1uF reduce leakage sensitivity and retain a similar nominal RC (47ms versus 51ms). The CM4 needs GLOBAL_EN low for more than 1ms. Confirm the actual pulse across temperature/capacitance, power startup and alarm clear/re-arm before enabling unattended timed wake; the nominal RC is not a guaranteed pulse width. See [independent circuit review](../review/INDEPENDENT-CIRCUIT-REVIEW.md).

## Audio profile

The assembled 4.7 nF ADC filter is intended for the 44.1/48 kHz prototype profile. Keep high-rate/ultrasonic modes disabled until settling and passband measurements pass. The board can instead populate the original 180 pF values for an r5-equivalent ADC bandwidth during comparison. The P3V3 output bypasses R104, preserving its original current path.

Use an explicit settling/mute interval after changing microphone power modes. The new nominal PIP RC takes about 4.6 ms to reach 99%; the existing coupling capacitors and amplifier start-up may require much longer, so derive the final mute interval from captured samples rather than removing the existing trim blindly.

## Supply telemetry

Read ADS1115 in single-shot mode at 128 SPS and +/-4.096 V range. This minimizes extra switching activity between reads. The four divider ratios are 16, 3, 2 and 3. Calibrate gain/offset against a bench meter before using thresholds. This monitors voltage, not current or remaining battery capacity. Read at startup and during transmit/load tests; log brownouts with the supply selected and modem state.

Sources: [TI ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf), [TI TCA9536](https://www.ti.com/lit/ds/symlink/tca9536.pdf), [RV-3032 application manual](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3032-C7_App-Manual.pdf), [Linux RV-3032 driver](https://github.com/torvalds/linux/blob/master/drivers/rtc/rtc-rv3032.c), [RC76xx manufacturer specification](https://source.sierrawireless.com/resources/airprime/hardware_specs_user_guides/rc76xx---product-technical-specification).
