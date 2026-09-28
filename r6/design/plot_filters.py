"""Calculated filter response only; these plots are not recorded audio spectra."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).resolve().parent.parent
f=np.geomspace(20,5e6,1000)
def att(r,c):return -10*np.log10(1+(2*np.pi*f*r*c)**2)
fig,ax=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
for c,style in [(10e-6,'-'),(4e-6,'--')]:ax[0].semilogx(f,att(100,c),style,label=f'{c*1e6:g} µF '+('nominal' if c==10e-6 else 'assumed effective'))
ax[0].axvline(8000,color='#888',lw=.8);ax[0].set_title('Plug-in bias supply: 100 Ω RC');ax[0].set_xlim(20,100000);ax[0].set_ylim(-65,1)
for c,name in [(180e-12,'r5: 180 pF'),(4.7e-9,'r6 prototype: 4.7 nF')]:ax[1].semilogx(f,att(200,c),label=name)
ax[1].axvspan(20,20000,color='#72bd91',alpha=.16,label='20 Hz–20 kHz');ax[1].axvline(1.38e6,color='#888',lw=.8);ax[1].set_title('ADC input: 200 Ω RC');ax[1].set_xlim(20,5e6);ax[1].set_ylim(-32,1)
for a in ax:a.set_xlabel('Frequency (Hz)');a.set_ylabel('Voltage transfer (dB)');a.grid(alpha=.2);a.legend(fontsize=8)
fig.suptitle('Ideal passive calculations — not measured audio-noise improvement',fontsize=12)
fig.savefig(base/'review/filter-response.svg');fig.savefig(base/'review/filter-response.png',dpi=150)
