"""Bench integration support for the Bugg r6 prototype.
Use with an smbus2.SMBus instance on /dev/i2c-1. No import-time hardware access.
These additions need integration into buggd and testing on a prototype.
"""
from dataclasses import dataclass
import time


class SupplyMonitor:
    ADDRESS = 0x48
    NAMES = ('input_v', 'system_5v', 'modem_3v7', 'usb_v')
    RATIOS = (16.0, 3.0, 2.0, 3.0)

    def __init__(self, bus, *, sleep=time.sleep, clock=time.monotonic):
        self.bus, self.sleep, self.clock = bus, sleep, clock

    def _read16(self, register):
        data = self.bus.read_i2c_block_data(self.ADDRESS, register, 2)
        if len(data) != 2:
            raise IOError('Incomplete ADS1115 register read')
        return (data[0] << 8) | data[1]

    def read_channel(self, channel):
        if channel not in range(4):
            raise ValueError('channel must be 0..3')
        # Single-shot, single-ended, +/-4.096 V, 128 SPS, comparator disabled.
        config = 0x8000 | ((4 + channel) << 12) | 0x0200 | 0x0100 | 0x0080 | 0x0003
        self.bus.write_i2c_block_data(self.ADDRESS, 1, [config >> 8, config & 0xff])
        self.sleep(0.001)
        deadline = self.clock() + 0.050
        while not self._read16(1) & 0x8000:
            if self.clock() >= deadline:
                raise TimeoutError('ADS1115 conversion did not finish')
            self.sleep(0.001)
        raw = self._read16(0)
        signed = raw - 65536 if raw & 0x8000 else raw
        if signed == 32767:
            raise ValueError('Supply monitor saturated; reading is not trustworthy')
        return signed * 0.000125 * self.RATIOS[channel]

    def read_all(self):
        return {name: self.read_channel(i) for i, name in enumerate(self.NAMES)}


@dataclass(frozen=True)
class ModemStatus:
    vgpio_present: bool
    safe_pulse_seen: bool


class ModemShutdownGuard:
    """Capture a fresh safe pulse, then wait for VGPIO discharge before rail removal.

    The caller owns serial AT I/O, USB shutdown and original modem GPIO drivers.
    I2C failures and timeouts keep the modem supply on. Any forced recovery must
    be a separately named, explicit operation in the host application.
    """
    ADDRESS = 0x41
    INPUT, OUTPUT, POLARITY, CONFIG, SPECIAL = 0, 1, 2, 3, 0x50

    def __init__(self, bus, *, sleep=time.sleep, clock=time.monotonic):
        self.bus, self.sleep, self.clock = bus, sleep, clock
        self.armed = False

    def _write(self, register, value):
        self.bus.write_byte_data(self.ADDRESS, register, value)

    def status(self):
        value = self.bus.read_byte_data(self.ADDRESS, self.INPUT)
        return ModemStatus(vgpio_present=not bool(value & 1), safe_pulse_seen=bool(value & 2))

    def arm(self):
        self.armed = False
        # Establish LOW before enabling P2 as an output. Hardware 10k pulldown
        # holds CLR low at reset, even against the expander's default weak pullup.
        self._write(self.OUTPUT, 0)
        self._write(self.POLARITY, 0)
        self._write(self.SPECIAL, 0x40)  # disable internal pullups; P3 remains an I/O
        self._write(self.CONFIG, 0x0b)   # P0/P1/P3 inputs; P2 output
        self.sleep(0.001)
        s = self.status()
        if s.safe_pulse_seen:
            raise IOError('Hardware safe-pulse latch did not clear')
        if not s.vgpio_present:
            raise IOError('VGPIO is absent before shutdown; cannot establish a fresh handshake')
        self._write(self.OUTPUT, 4)
        self.armed = True

    def wait_ready(self, timeout=30.0, stable_time=0.1):
        if not self.armed:
            raise RuntimeError('Arm immediately before sending AT!POWERDOWN')
        deadline, low_since = self.clock() + timeout, None
        while self.clock() < deadline:
            # Detect an expander reset/brownout rather than treating default all-high inputs as safe.
            if self.bus.read_byte_data(self.ADDRESS, self.CONFIG) & 0xf != 0xb:
                self.armed = False
                raise IOError('Modem status expander reset during shutdown')
            if not self.bus.read_byte_data(self.ADDRESS, self.OUTPUT) & 4:
                self.armed = False
                raise IOError('Safe-pulse latch is not armed')
            s, now = self.status(), self.clock()
            if s.safe_pulse_seen and not s.vgpio_present:
                if low_since is None:
                    low_since = now
                elif now - low_since >= stable_time:
                    self.armed = False
                    return
            else:
                low_since = None
            self.sleep(0.01)
        self.armed = False
        raise TimeoutError('No complete safe-pulse/VGPIO handshake; leave +3V7 enabled')

    def shutdown(self, request_powerdown, disable_host_interfaces, remove_supply, timeout=30.0):
        """Issue AT!POWERDOWN, promptly isolate interfaces, then verify shutdown.

        request_powerdown must finish transmitting the command and return promptly;
        it must not wait for VGPIO loss, USB disconnection, or a shutdown indication.
        An optional immediate command acknowledgement must not delay isolation past
        VGPIO falling. The host integration must validate this timing on hardware.
        disable_host_interfaces must put connected I/O in high-Z or LOW and return
        only when that is complete. Either callback raising leaves supply enabled.
        """
        self.arm()
        try:
            request_powerdown()
            # RC76xx Rev16 Figure 4-2 note (a): isolate BEFORE VGPIO switches off,
            # not merely before removing VBATT (the separate section 4.24.5 rule).
            disable_host_interfaces()
            self.wait_ready(timeout)
            remove_supply()
        finally:
            self.armed = False
