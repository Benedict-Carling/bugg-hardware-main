"""RV-3032 support for the r6 CR1220-backed RTC.
Use only with exclusive I2C ownership (kernel RTC driver unbound).
Register definitions/sequence: Micro Crystal application manual Rev 1.3.
"""
from datetime import datetime, timedelta, timezone
import time

class RTC3032:
    ADDRESS = 0x51
    def __init__(self, bus, *, sleep=time.sleep, clock=time.monotonic):
        self.bus, self.sleep, self.clock = bus, sleep, clock
    def read(self, reg):return self.bus.read_byte_data(self.ADDRESS, reg)
    def write(self, reg, value):self.bus.write_byte_data(self.ADDRESS, reg, value)
    def update(self, reg, mask, value):self.write(reg, (self.read(reg) & ~mask) | (value & mask))
    def _ready(self):
        deadline=self.clock()+.2
        while self.read(0x0e)&4:
            if self.clock()>deadline:raise TimeoutError('RTC EEPROM remains busy')
            self.sleep(.002)
        if self.read(0x0e)&8:raise IOError('RTC EEPROM write-failure flag is set')
    def configure_cr1220(self):
        self.sleep(.1)  # Initial factory EEPROM-to-RAM refresh takes about 66 ms.
        self._ready()
        current=self.read(0xc0)
        target=(current&0x0c)|0x50  # preserve resistor field, charger off, DSM, CLKOUT off
        if current==target:return False
        if self.read(0xca)!=0:raise IOError('RTC EEPROM is password-protected; refusing to alter it')
        ctrl=self.read(0x10)
        self.write(0x10,ctrl|4)
        try:
            self._ready()
            # Disable backup switching and charging while accessing EEPROM.
            self.write(0xc0,(current&0x0c)|0x40)
            self.write(0x3d,0xc0)
            self.write(0x3e,target)
            self.write(0x3f,0x21)  # write just PMU, never overwrite factory trim registers
            self.sleep(.010);self._ready()
            self.write(0x3f,0x12)  # refresh persisted configuration into RAM
            self.sleep(.002);self._ready()
            if self.read(0xc0)!=target:raise IOError('RTC PMU did not verify after EEPROM refresh')
        finally:
            self.write(0x10,ctrl)
        return True
    @staticmethod
    def bcd(n):return (n//10)*16+n%10
    @staticmethod
    def unbcd(n):
        if n&15>9 or n>>4>9:raise ValueError('Invalid BCD from RTC')
        return (n>>4)*10+(n&15)
    def set_time(self, utc):
        if utc.tzinfo is None:raise ValueError('Use a timezone-aware UTC datetime')
        utc=utc.astimezone(timezone.utc)
        if not 2000<=utc.year<=2099:raise ValueError('RTC calendar range is 2000..2099')
        data=[self.bcd(n) for n in [utc.second,utc.minute,utc.hour,utc.weekday(),utc.day,utc.month,utc.year-2000]]
        self.bus.write_i2c_block_data(self.ADDRESS,1,data)
        self.update(0x11,1,0)  # oscillator/calendar running
        self.update(0x0d,3,0)  # acknowledge POR/voltage-low only after setting valid time
    def get_time(self):
        if self.read(0x0d)&3:raise ValueError('RTC time is invalid after power/voltage loss')
        data=self.bus.read_i2c_block_data(self.ADDRESS,1,7)
        if len(data)!=7:raise IOError('Incomplete RTC calendar read')
        sec,minute,hour,weekday,day,month,year=[self.unbcd(v) for v in data]
        return datetime(2000+year,month,day,hour,minute,sec,tzinfo=timezone.utc)
    def clear_wake(self):
        # Disable timer first, then interrupt sources, then flags: prevents inadvertent GLOBAL_EN pulses.
        self.update(0x10,8,0)
        self.update(0x11,0x3c,0)
        self.update(0x0d,0x38,0)
    def alarm_at(self, utc):
        """One calendar wake at minute resolution, rounded UP; caller then halts CM4.
        Call clear_wake early at next boot. This bypasses the Linux driver's need
        for a GPIO IRQ, using the retained hardware GLOBAL_EN wake path.
        """
        if utc.tzinfo is None:raise ValueError('Use a timezone-aware datetime')
        utc=utc.astimezone(timezone.utc)
        if utc.second or utc.microsecond:utc=utc.replace(second=0,microsecond=0)+timedelta(minutes=1)
        now=self.get_time()
        if not timedelta(minutes=2)<=utc-now<=timedelta(days=27):
            raise ValueError('Wake must be 2 minutes..27 days ahead (time to halt; no month ambiguity)')
        self.clear_wake()
        self.bus.write_i2c_block_data(self.ADDRESS,0x08,[self.bcd(utc.minute),self.bcd(utc.hour),self.bcd(utc.day)])
        self.update(0x14,0x40,0)  # no CLKOUT-dependent interrupt delay
        self.update(0x11,0x08,0x08)
        return utc

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Provision Bugg r6 RTC with CR1220 charging disabled; exclusive bus ownership required')
    parser.add_argument('--bus',type=int,default=1)
    args=parser.parse_args()
    from smbus2 import SMBus
    with SMBus(args.bus) as bus:
        changed=RTC3032(bus).configure_cr1220()
        print('PMU programmed and verified' if changed else 'PMU already correct; no EEPROM write')
