import unittest
from datetime import datetime,timedelta,timezone
from rtc_config import RTC3032
from test_r6_support import Clock
class RTCBus:
 def __init__(self):self.r={};self.e={};self.writes=[]
 def read_byte_data(self,a,r):return self.r.get(r,0)
 def write_byte_data(self,a,r,v):
  self.writes.append((r,v));self.r[r]=v
  if r==0x3f and v==0x21:self.e[self.r[0x3d]]=self.r[0x3e]
  if r==0x3f and v==0x12:self.r.update(self.e)
 def write_i2c_block_data(self,a,r,v):
  for i,n in enumerate(v):self.write_byte_data(a,r+i,n)
 def read_i2c_block_data(self,a,r,n):return [self.r.get(r+i,0) for i in range(n)]
class Tests(unittest.TestCase):
 def setUp(self):
  self.b=RTCBus();self.c=Clock();self.r=RTC3032(self.b,sleep=self.c.sleep,clock=self.c.now)
 def test_cr1220_never_enables_charger(self):
  self.assertTrue(self.r.configure_cr1220());self.assertEqual(self.b.e[0xc0],0x50)
  self.assertTrue(all(not v&3 for reg,v in self.b.writes if reg in [0xc0,0x3e]));self.assertEqual(self.b.r[0x10],0)
 def test_no_repeat_eeprom_wear(self):
  self.b.r[0xc0]=0x50;self.assertFalse(self.r.configure_cr1220());self.assertEqual(self.b.writes,[])
 def test_factory_calibration_preserved(self):
  self.b.e[0xc1]=0xa5;self.r.configure_cr1220();self.assertEqual(self.b.e[0xc1],0xa5)
 def test_password_does_not_trigger_guessing(self):
  self.b.r[0xca]=255
  with self.assertRaises(IOError):self.r.configure_cr1220()
  self.assertEqual(self.b.writes,[])
 def test_time_roundtrip(self):
  now=datetime(2026,9,28,13,45,59,tzinfo=timezone.utc);self.r.set_time(now);self.assertEqual(self.r.get_time(),now)
 def test_alarm_rounds_up_and_enables_only_alarm(self):
  now=datetime(2026,9,28,13,45,59,tzinfo=timezone.utc);self.r.set_time(now)
  target=self.r.alarm_at(now+timedelta(minutes=5));self.assertEqual(target.minute,51);self.assertEqual(target.second,0)
  self.assertEqual(self.b.r[0x11]&0x3c,8);self.assertEqual(self.b.r[0x08],0x51)
 def test_bad_time_refused(self):
  self.b.r[0x0d]=1
  with self.assertRaises(ValueError):self.r.get_time()
 def test_month_ambiguity_rejected(self):
  now=datetime(2026,9,28,tzinfo=timezone.utc);self.r.set_time(now)
  with self.assertRaises(ValueError):self.r.alarm_at(now+timedelta(days=28))
if __name__=='__main__':unittest.main()
