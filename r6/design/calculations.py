"""Reproducible, schematic-checked headline calculations, with explicit limits."""
import json,math,xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
x=ET.parse(BASE/'review/r6.xml').getroot();vals={c.get('ref'):c.findtext('value') for c in x.findall('components/comp')}
assert vals['R104']=='100R' and vals['C83']=='10uF'
assert all(vals[r]=='200R' for r in ['R61','R62']) and all(vals[r]=='4.7nF' for r in ['C75','C76'])
def loss(f,r,c):return 10*math.log10(1+(2*math.pi*f*r*c)**2)
rows=[]
for f in [8000,20000,80000,1250000,1380000,1400000,1500000]:
 old=loss(f,200,180e-12);new=loss(f,200,4.7e-9)
 rows.append(dict(frequency_hz=f,r5_loss_db=old,r6_loss_db=new,extra_rejection_db=new-old))
# C83 is an existing 6.3 V X5R. 4..10 uF is a scenario range, NOT a manufacturer-guaranteed bound.
bias=[{'effective_capacitance_uF':c*1e6,'rejection_8khz_db':loss(8000,100,c),'tau_ms':100*c*1000} for c in [4e-6,6e-6,10e-6]]
result={'evidence':'Calculated passive RC response and manufacturer RTC tolerance; not measured audio noise or whole-board current.',
 'adc':{'r5_C_pF':180,'r6_C_nF':4.7,'R_ohm':200,'r6_pole_Hz':1/(2*math.pi*200*4.7e-9),'response':rows,
 'full_scale_step_16bit_halfLSB_settling_us':math.log(2**17)*200*4.7e-9*1e6,
 'limits':'Ideal RC only. Does not include ADC kickback, LM4562 dynamics, PCB parasitics or sample timing. 4.7 nF is the 44.1/48 kHz population; higher rates require separate validation/population.'},
 'pip':{'series_R_ohm':100,'C83_nominal_uF':10,'scenarios':bias,'drop_at_0p5mA_mV':50,'drop_at_1mA_mV':100,
 'nominal_99percent_startup_ms':-math.log(.01)*100*10e-6*1000,
 'limits':'Ripple-to-bias transfer only. Capacitance derating, load impedance and PCB coupling affect actual response. Filter is bypassed by the P3V3 supply branch.'},
 'clock':{'r5_tolerance_ppm':5,'r6_tolerance_ppm':2.5,'temperature_range_C':[-40,85],'r5_seconds_per_day':5e-6*86400,'r6_seconds_per_day':2.5e-6*86400,'ratio':2,
 'limits':'Initial manufacturer timekeeping specifications over temperature; excludes aging, board stress and calendar/software errors. RTC oscillator is independent of the audio sample clock.'},
 'telemetry':{'new_channels':4,'channels':['external input','system +5V','modem +3V7','USB VBUS'],'adc_bits':16,'adc_lsb_uV_at_selected_gain':125,'rail_lsb_mV':[2,.375,.25,.375],
 'limits':'These are code resolutions, not voltage accuracy. No shunt is fitted, so there is no current, watt-hour or battery state-of-charge measurement.'},
 'modem':{'signals_added':2,'safe_pulse_ms':13.26,'nominal_pulse_end_to_vgpio_off_ms':7.8,'latch':True,'host_stable_off_guard_ms':100,
 'limits':'Hardware and software design benefit; field reliability and shutdown timing require hardware tests.'}}
(BASE/'review/calculations.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
