"""Audit actual finished CAD against the upstream board and exported schematic."""
import json,collections,xml.etree.ElementTree as ET,hashlib,re
import pcbnew as p
from common import *
board_path=OUT/(PROJECT+'.kicad_pcb')
board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest()
b=p.LoadBoard(str(board_path))
def xy(v):return (p.ToMM(v.x),p.ToMM(v.y))
def signature(f):
 return dict(pos=xy(f.GetPosition()),angle=f.GetOrientationDegrees(),layer=int(f.GetLayer()),fpid=str(f.GetFPID().GetLibItemName()),pads=[dict(number=a.GetNumber(),pos=xy(a.GetPosition()),size=xy(a.GetSize()),drill=xy(a.GetDrillSize()),layers=list(a.GetLayerSet().Seq())) for a in f.Pads()])
fps={f.GetReference():f for f in b.GetFootprints()}
baseline=json.loads((BASE/'review/mechanical-baseline.json').read_text())
actual=json.loads(json.dumps({r:signature(fps[r]) for r in baseline}))
assert actual==baseline, [r for r in baseline if actual[r]!=baseline[r]]
# Compare every outline primitive, excluding UUID, lock and file formatting.
def outline(board):
 result=[]
 for s in board.GetDrawings():
  if s.GetLayer()!=p.Edge_Cuts:continue
  result.append((int(s.GetShape()),xy(s.GetStart()),xy(s.GetEnd()),xy(s.GetCenter()),s.GetWidth(),s.GetArcAngle().AsDegrees()))
 return sorted(result)
s=p.LoadBoard(str(SOURCE/'bugg-main-r5.kicad_pcb'))
source_fps={f.GetReference():f for f in s.GetFootprints()}
# Compare directly against r5 as well as the stored baseline. Include pad
# shape/orientation and drill geometry, which affect mating connectors and holes.
def pad_mechanics(f):
 return sorted((a.GetNumber(),xy(a.GetPosition()),xy(a.GetSize()),xy(a.GetDrillSize()),
                int(a.GetShape()),int(a.GetDrillShape()),int(a.GetAttribute()),
                a.GetOrientationDegrees(),xy(a.GetOffset()),tuple(a.GetLayerSet().Seq()))
               for a in f.Pads())
assert {r:signature(source_fps[r]) for r in baseline}=={r:signature(fps[r]) for r in baseline},'Source interface geometry changed'
assert all(pad_mechanics(source_fps[r])==pad_mechanics(fps[r]) for r in baseline),'Interface pad mechanics changed'
assert outline(s)==outline(b),'Outline changed'
assert b.GetCopperLayerCount()==s.GetCopperLayerCount()==6
assert b.GetDesignSettings().GetBoardThickness()==s.GetDesignSettings().GetBoardThickness()
x=ET.parse(BASE/'review/r6.xml').getroot();expected={};schrefs=set()
for c in x.findall('components/comp'):
 if any(z.get('name')=='exclude_from_board' for z in c.findall('property')):continue
 ref=c.get('ref');schrefs.add(ref);assert fps[ref].GetValue()==c.findtext('value'),ref
for net in x.findall('nets/net'):
 for n in net.findall('node'):
  name=net.get('name')
  if name.startswith('unconnected-'):name=name.replace('/','{slash}')
  expected[(n.get('ref'),n.get('pin'))]=name
assert set(fps)==schrefs, set(fps)^schrefs
count=0
for ref,f in fps.items():
 for pad in f.Pads():
  want=expected.get((ref,pad.GetNumber()))
  if want is not None:
   assert pad.GetNetname()==want,(ref,pad.GetNumber(),pad.GetNetname(),want);count+=1
assert 'SW1' not in fps and not any(f'TP{i}' in fps for i in range(1,10))
def service_refs(footprints,kind):
 return {r for r,f in footprints.items() if
         (kind=='testpoint' and (re.fullmatch(r'TP?\d+',r) or 'testpoint' in str(f.GetFPID()).lower())) or
         (kind=='switch' and (re.fullmatch(r'SW\d+',r) or any(k in str(f.GetFPID()).lower() for k in ['switch','button'])))}
for kind in ['testpoint','switch']:
 assert service_refs(fps,kind)==service_refs(source_fps,kind),f'Added or removed {kind}'
# Every USB and microphone input segment and via must remain exactly as
# published, including via drills and layer pairs (not merely their positions).
def copper(board,net):
 result=[]
 for t in board.GetTracks():
  if t.GetNetname()!=net:continue
  if isinstance(t,p.PCB_VIA):
   shape=('via',xy(t.GetPosition()),int(t.GetViaType()),int(t.TopLayer()),int(t.BottomLayer()),t.GetDrillValue(),
          tuple((int(layer),t.GetWidth(layer)) for layer in board.GetEnabledLayers().CuStack() if t.IsOnLayer(layer)))
  elif isinstance(t,p.PCB_ARC):
   shape=('arc',int(t.GetLayer()),xy(t.GetStart()),xy(t.GetMid()),xy(t.GetEnd()),t.GetWidth())
  else:
   shape=('track',int(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),t.GetWidth())
  result.append(shape)
 return sorted(result)
usb={n:copper(b,n)==copper(s,n) for n in ['/USB_DP','/USB_DN']}
mic={n:copper(b,n)==copper(s,n) for n in ['/MIC_IN_P','/MIC_IN_N']}
assert all(copper(s,n) for n in [*usb,*mic]),'Missing protected source net'
assert all(usb.values()),('USB copper changed',usb)
assert all(mic.values()),('Microphone input copper changed',mic)
assert hashlib.sha256(board_path.read_bytes()).hexdigest()==board_sha256,'Board changed during verification; rerun on a stable board'
result={'fixed_interfaces_unchanged':len(baseline),'interface_pad_mechanics_unchanged':True,'outline_unchanged':True,'copper_layers':6,'thickness_mm':p.ToMM(b.GetDesignSettings().GetBoardThickness()),'footprints':len(fps),'schematic_pad_net_checks':count,'added_button_and_nine_testpoints_removed':True,'original_testpoints_preserved':len(service_refs(fps,'testpoint')),'original_switches_preserved':len(service_refs(fps,'switch')),'usb_original_copper_exact':usb,'mic_original_copper_exact':mic,'board_sha256':board_sha256}
(BASE/'review/cad-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
