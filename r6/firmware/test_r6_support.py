"""Meaningful fault-path and electrical-scaling tests; no physical hardware claims."""
import unittest
from r6_support import SupplyMonitor, ModemShutdownGuard

class Clock:
    def __init__(self): self.t=0
    def now(self): return self.t
    def sleep(self,seconds): self.t+=seconds

class Bus:
    def __init__(self,clock):
        self.c=clock;self.reg={0:0,1:0,2:0,3:15};self.events=[];self.fail=False
        self.conversion=1000;self.config16=0;self.ready=True
    def write_byte_data(self,a,r,v):self.reg[r]=v
    def read_byte_data(self,a,r):
        if self.fail:raise IOError('bus fault')
        if r==0:
            state=self.reg[0]
            for t,value in self.events:
                if self.c.t>=t:state=value
            return state
        return self.reg[r]
    def write_i2c_block_data(self,a,r,v):self.config16=v[0]<<8|v[1]
    def read_i2c_block_data(self,a,r,length):
        v=(self.config16 if self.ready else self.config16&0x7fff) if r==1 else self.conversion
        return [v>>8,v&255]

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=Clock();self.b=Bus(self.c);self.g=ModemShutdownGuard(self.b,sleep=self.c.sleep,clock=self.c.now)
        self.actions=[]
    def shutdown(self):
        self.g.shutdown(lambda:self.actions.append('AT'),lambda:self.actions.append('interfaces'),lambda:self.actions.append('rail'),timeout=.5)
    def test_complete_handshake(self):
        self.b.events=[(.03,2),(.05,3)]
        isolated_at=[]
        def isolate():
            isolated_at.append(self.c.t)
            self.actions.append('interfaces')
            self.assertTrue(self.g.status().vgpio_present)
        self.g.shutdown(lambda:self.actions.append('AT'),isolate,lambda:self.actions.append('rail'),timeout=.5)
        self.assertEqual(self.actions,['AT','interfaces','rail']);self.assertGreaterEqual(self.c.t,.15)
        self.assertLess(isolated_at[0],.05)
    def test_interface_isolation_failure_never_cuts_supply(self):
        self.b.events=[(.03,2),(.05,3)]
        def isolate():raise IOError('host interface isolation failed')
        with self.assertRaises(IOError):
            self.g.shutdown(lambda:self.actions.append('AT'),isolate,lambda:self.actions.append('rail'))
        self.assertEqual(self.actions,['AT']);self.assertFalse(self.g.armed)
    def test_command_failure_never_cuts_supply(self):
        def request():raise IOError('command was not transmitted')
        with self.assertRaises(IOError):
            self.g.shutdown(request,lambda:self.actions.append('interfaces'),lambda:self.actions.append('rail'))
        self.assertEqual(self.actions,[]);self.assertFalse(self.g.armed)
    def test_short_pulse_latched_before_late_linux_poll(self):
        # Hardware latch retains the event even if the process only runs after VGPIO has fallen.
        self.b.events=[(.03,3)];self.g.arm();self.c.sleep(.2);self.g.wait_ready(timeout=.5)
    def test_no_pulse_never_cuts_supply(self):
        self.b.events=[(.03,1)]
        with self.assertRaises(TimeoutError):self.shutdown()
        self.assertEqual(self.actions,['AT','interfaces'])
    def test_pulse_without_vgpio_off_never_cuts_supply(self):
        self.b.events=[(.03,2)]
        with self.assertRaises(TimeoutError):self.shutdown()
        self.assertEqual(self.actions,['AT','interfaces'])
    def test_stale_latch_rejected(self):
        self.b.reg[0]=2
        with self.assertRaises(IOError):self.shutdown()
        self.assertEqual(self.actions,[])
    def test_expander_reset_rejected(self):
        self.g.arm();self.b.reg[3]=15
        with self.assertRaises(IOError):self.g.wait_ready()
    def test_bus_fault_never_cuts_supply(self):
        self.b.fail=True
        with self.assertRaises(IOError):self.shutdown()
        self.assertEqual(self.actions,[])
    def test_arm_required(self):
        with self.assertRaises(RuntimeError):self.g.wait_ready()
    def test_voltage_scaling_and_mux(self):
        a=SupplyMonitor(self.b,sleep=self.c.sleep,clock=self.c.now)
        for ch,expect in enumerate([2,.375,.25,.375]):
            self.assertAlmostEqual(a.read_channel(ch),expect);self.assertEqual((self.b.config16>>12)&7,4+ch)
    def test_adc_timeout(self):
        self.b.ready=False;a=SupplyMonitor(self.b,sleep=self.c.sleep,clock=self.c.now)
        with self.assertRaises(TimeoutError):a.read_channel(0)
    def test_adc_saturation(self):
        self.b.conversion=32767;a=SupplyMonitor(self.b,sleep=self.c.sleep,clock=self.c.now)
        with self.assertRaises(ValueError):a.read_channel(0)
    def test_vgpio_bounce_restarts_settling(self):
        self.b.events=[(.03,3),(.09,2),(.12,3)];self.shutdown();self.assertGreaterEqual(self.c.t,.22)
if __name__=='__main__':unittest.main()
