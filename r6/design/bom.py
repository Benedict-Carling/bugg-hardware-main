"""Review BOM and component delta from actual schematic XML, without vendor inference."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent

def read(path):
 x=ET.parse(path).getroot();out={}
 for c in x.findall('components/comp'):
  f={f.get('name'):(f.text or '').strip() for f in c.findall('fields/field')}
  if any(p.get('name')=='exclude_from_bom' for p in c.findall('property')):continue
  out[c.get('ref')]={'value':c.findtext('value'),'footprint':c.findtext('footprint'),'mpn':f.get('MPN',''),'manufacturer':f.get('Manufacturer',''),'sheet':c.find('sheetpath').get('names')}
 return out
old=read(BASE/'review/r5.xml');new=read(BASE/'review/r6.xml');changes={}
for ref,item in new.items():
 if ref not in old:changes[ref]={'status':'added','new':item}
 elif any(item.get(k)!=old[ref].get(k) for k in ['value','footprint','mpn']):changes[ref]={'status':'changed','old':old[ref],'new':item}
for ref,item in old.items():
 if ref not in new:changes[ref]={'status':'removed','old':item}
(BASE/'review/bom.json').write_text(json.dumps(new,indent=2)+'\n')
(BASE/'review/bom-delta.json').write_text(json.dumps(changes,indent=2)+'\n')
lines=['# Component changes','','From exported native schematics. Original unspecified MPN fields remain unspecified; this is not a supplier stock check. Existing bare test pads are not extra r6 test points. The passive ADC-filter alternative is 180 pF at C75/C76.','','| Reference | Change | r6 value | r6 MPN |','|---|---|---|---|']
for r,z in changes.items():
 item=z.get('new',{});lines.append(f"| {r} | {z['status']} | {item.get('value','—')} | {item.get('mpn','') or 'Unspecified in source'} |")
(BASE/'review/BOM-CHANGES.md').write_text('\n'.join(lines)+'\n')
print(len(new),'BOM entries;',len(changes),'changed or added entries.')
