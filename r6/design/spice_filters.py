"""Independent ngspice AC cross-check of the ideal passive headline calculations."""
from pathlib import Path
import subprocess,json,math
BASE=Path(__file__).resolve().parent.parent;dest=BASE/'review/spice';dest.mkdir(exist_ok=True)
cases=[('adc-r5',200,180e-12,1380000),('adc-r6',200,4.7e-9,1380000),('adc-r6-audio',200,4.7e-9,20000),('bias-nominal',100,10e-6,8000),('bias-derated-scenario',100,4e-6,8000)]
results=[]
for name,r,c,f in cases:
 out=dest/(name+'.dat');net=dest/(name+'.cir')
 net.write_text(f'''Ideal passive filter, {name}; not a switched ADC model
V1 in 0 AC 1
R1 in out {r}
C1 out 0 {c}
.control
ac lin 1 {f} {f}
let gain_db = db(v(out))
wrdata {out.resolve()} gain_db
quit
.endc
.end
''')
 run=subprocess.run(['/opt/homebrew/bin/ngspice','-b',str(net)],capture_output=True,text=True,check=True)
 (dest/(name+'.log')).write_text(run.stdout+run.stderr)
 db=float(out.read_text().split()[-1]);expected=-10*math.log10(1+(2*math.pi*f*r*c)**2)
 assert abs(db-expected)<1e-6,(name,db,expected)
 results.append({'case':name,'frequency_hz':f,'ngspice_gain_db':db,'formula_gain_db':expected})
(BASE/'review/spice-verification.json').write_text(json.dumps(results,indent=2)+'\n');print('5 ideal AC cases agree with ngspice within 0.000001 dB.')
