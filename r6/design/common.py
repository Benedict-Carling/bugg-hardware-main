"""Small KiCad S-expression helpers; retain untouched source blocks verbatim."""
import json, re, uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
SOURCE=BASE.parent/'r5/src'
OUT=BASE/'src'
PROJECT='bugg-main-r6'
KCLI=HERE/'kcli.sh'
def uid(): return str(uuid.uuid4())
def q(s): return json.dumps(str(s),ensure_ascii=False)
def children(t):
 depth=0; quoted=False; escaped=False; start=0
 for i,c in enumerate(t):
  if quoted:
   if escaped: escaped=False
   elif c=='\\': escaped=True
   elif c=='"': quoted=False
  elif c=='"': quoted=True
  elif c=='(':
   depth+=1
   if depth==2: start=i
  elif c==')':
   if depth==2: yield start,i+1
   depth-=1

def blocks(t,key):
 return [(a,b,t[a:b]) for a,b in children(t) if re.match(r'\('+re.escape(key)+r'(?:\s|\))',t[a:b])]
def prop(t,name):
 m=re.search(r'\(property '+q(name)+r' ("(?:[^"\\]|\\.)*")',t)
 return json.loads(m[1]) if m else None

def change_prop(t,name,value):
 return re.sub(r'(\(property '+q(name)+r' )"(?:[^"\\]|\\.)*"',lambda m:m[1]+q(value),t,count=1)
def direct(t,key):
 return blocks(t,key)[0][2]
def at(t):
 s=direct(t,'at');return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',s)]
def append(t,s):
 i=t.rfind(')');return t[:i]+s+'\n'+t[i:]
def label(name,x,y):
 return f'(global_label {q(name)} (shape passive) (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {q(uid())}))'
def get_symbol(t,ref):
 return next((a,b,s) for a,b,s in blocks(t,'symbol') if prop(s,'Reference')==ref)
def pin_xy(t,ref,pin):
 import math
 syms=[s for _,_,s in blocks(t,'symbol') if prop(s,'Reference')==ref]
 libs=direct(t,'lib_symbols')
 for s in syms:
  lib=json.loads(re.search(r'\(lib_id ("[^"]+")',s)[1]);u=int(re.search(r'\(unit (\d+)',s)[1])
  lb=next(b for _,_,b in blocks(libs,'symbol') if b.startswith('(symbol '+q(lib)+'\n') or b.startswith('(symbol '+q(lib)+' '))
  for _,_,unit in blocks(lb,'symbol'):
   name=json.loads(re.match(r'\(symbol ("[^"]+")',unit)[1]);un=int(name.rsplit('_',2)[-2])
   if un not in (0,u):continue
   for _,_,p in blocks(unit,'pin'):
    if not re.search(r'\(number '+q(pin)+r'\s',p):continue
    px,py,*_=at(p);x,y,ang=at(s)
    if '(mirror x)' in s:py=-py
    if '(mirror y)' in s:px=-px
    a=math.radians(ang)
    return round(x+px*math.cos(a)-py*math.sin(a),6),round(y-(px*math.sin(a)+py*math.cos(a)),6)
 raise KeyError((ref,pin))
def hook_pin(t,ref,pin,name,disconnect=False):
 x,y=pin_xy(t,ref,pin)
 edits=[]
 for a,b,s in blocks(t,'no_connect'):
  if at(s)[:2]==[x,y]:edits.append((a,b,''))
 if disconnect:
  # Remove only the immediate wire at this terminal, replacing its connection with a label.
  found=0
  for a,b,s in blocks(t,'wire'):
   points=[tuple(map(float,z)) for z in re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)',s)]
   if (x,y) in points:edits.append((a,b,''));found+=1
  assert found==1,(ref,pin,(x,y),found)
 for a,b,s in sorted(edits,reverse=True):t=t[:a]+s+t[b:]
 return append(t,label(name,x,y))
