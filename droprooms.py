#!/usr/bin/env python3
"""Original offline faux-3D helix tower dropper with a backrooms mood. Stdlib only."""
import curses,os,json,random,time,sys
from pathlib import Path
from ui import put,run
VERSION='1.0.0'
RECORD=Path.home()/'.local/share/droprooms/best.json'
FLOORS_PER_LEVEL=12
class Tower:
 def __init__(self,seed=None,level=1):
  self.rng=random.Random(seed);self.level=level;self.rot=0.;self.index=0
  self.score=0;self.over=False;self.scroll=0.;self.drops=0
  self.message='Left/Right rotates the tower. Drop the ball through the gaps!'
  self.floors=[];self.extend(FLOORS_PER_LEVEL)
 def gap_width(self):return max(50,110-8*self.level)
 def danger_count(self):return min(4,self.level)
 def extend(self,n):
  for _ in range(n):
   gap=self.rng.uniform(0,360);arcs=[]
   for _ in range(self.danger_count()):
    while True:
     start=self.rng.uniform(0,360);width=self.rng.uniform(20,45)
     a=(start-gap)%360
     if a>self.gap_width()/2+width and 360-a>self.gap_width()/2+width:break
    arcs.append((start,width))
   self.floors.append({'gap':gap,'gw':self.gap_width(),'danger':arcs})
 def angle_in(self,ang,start,width):
  return abs(((ang-start+180)%360)-180)<=width/2 if width<360 else True
 def segment_at(self,floor,ang):
  a=ang%360
  if self.angle_in(a,floor['gap'],floor['gw']):return 'gap'
  for start,width in floor['danger']:
   if self.angle_in(a,start,width):return 'danger'
  return 'solid'
 def rotate(self,dt,dirn):self.rot=(self.rot+dirn*160*dt)%360
 def ball_angle(self):return (-self.rot)%360
 def land(self):
  """Ball touched the current floor. Returns 'gap','danger' or 'solid'."""
  seg=self.segment_at(self.floors[self.index],self.ball_angle())
  if seg=='danger':self.over=True;self.message='Sizzled on a bad tile. R restarts.'
  return seg
 def drop(self):
  self.index+=1;self.score+=1;self.scroll=1.;self.drops+=1
  if self.drops%FLOORS_PER_LEVEL==0:
   self.level+=1;self.score+=10
   self.message='Level '+str(self.level)+'! Gaps shrink, bad tiles grow.'
  self.extend(1)
 def tick(self,dt):
  self.scroll=max(0.,self.scroll-dt*4)
def best():
 try:
  if RECORD.is_symlink():return 0
  return max(0,int(json.loads(RECORD.read_text()).get('best',0)))
 except (OSError,ValueError,TypeError,AttributeError):return 0
def save(score):
 try:
  if any(p.is_symlink() for p in [RECORD,*RECORD.parents]):return False
  RECORD.parent.mkdir(parents=True,exist_ok=True,mode=0o700);tmp=RECORD.with_suffix('.tmp');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as f:json.dump({'best':max(score,best())},f)
  tmp.replace(RECORD);return True
 except OSError:return False
def palette():
 if not curses.has_colors():return False
 curses.start_color();curses.use_default_colors()
 values=[(220,-1),(255,-1),(160,-1),(245,-1),(94,-1)] if curses.COLORS>=256 else [(3,-1),(7,-1),(1,-1),(7,-1),(3,-1)]
 for i,(fg,bg) in enumerate(values,1):curses.init_pair(i,fg,bg)
 return True
def play(s):
 h,w=s.getmaxyx();g=Tower();last=time.monotonic();colors=palette();paused=False
 bounce=0.;dirn=0;recorded=False;high=best();flicker=0
 def color(i):return curses.color_pair(i) if colors else 0
 while True:
  s.timeout(30);key=s.getch();now=time.monotonic();dt=now-last;last=now;h,w=s.getmaxyx();s.erase()
  if key in (27,ord('q'),ord('Q')):return
  if key in (ord('p'),ord('P')):paused=not paused
  if key in (ord('r'),ord('R')):g=Tower();recorded=False;paused=False;bounce=0
  if h<24 or w<70:put(s,1,1,'Resize to 70x24. Simulation paused. Q quits.');s.refresh();continue
  if not g.over and not paused:
   if key==curses.KEY_LEFT or key==ord('a'):dirn=-1
   elif key==curses.KEY_RIGHT or key==ord('d'):dirn=1
   else:dirn=0
   g.rotate(dt,dirn);g.tick(dt)
   bounce+=dt*3.2
   if bounce>=1:
    bounce=0;seg=g.land()
    if seg=='gap':g.drop()
  if g.over and not recorded:g.message+=' Best saved.' if save(g.score) else ' Save unavailable.';recorded=True;high=max(high,best())
  # backrooms ceiling with flickering fluorescent panels
  flicker=g.rng.random()
  for x in range(w):put(s,0,x,'_',color(5))
  for lx in range(8,w-8,16):
   if flicker>.12:put(s,1,lx,'=||||=',color(2)|curses.A_BOLD)
  put(s,2,2,'DROPROOMS | SCORE '+str(g.score)+' | LEVEL '+str(g.level)+' | BEST '+str(high)+(' | PAUSED' if paused else ''),color(1)|curses.A_BOLD)
  put(s,3,2,g.message,color(2))
  # tower: 6 visible floors, perspective-narrowed toward the top
  base=7;step=3
  for slot in range(6):
   fi=g.index+slot;y=base+(5-slot)*step-round(g.scroll*step)
   if fi>=len(g.floors):continue
   depth=5-slot;halfw=max(8,(w//2-6)*(6-depth)//6);cx=w//2
   floor=g.floors[fi]
   for x in range(cx-halfw,cx+halfw):
    t=(x-cx)/max(1,halfw);ang=(t*90-g.rot)%360
    seg=g.segment_at(floor,ang)
    yy=y-round((1-t*t)*1.4)
    if seg=='gap':continue
    put(s,yy,x,'#' if seg=='solid' else 'X',color(1) if seg=='solid' else color(3)|curses.A_BOLD)
  # ball bounces in front of the current floor
  by=base+5*step-round(g.scroll*step)-2-round(abs(0.5-(bounce%1))*2*2.4)
  put(s,max(4,by),w//2,'()',color(2)|curses.A_BOLD)
  put(s,h-2,2,'Left/Right or A/D rotate | P pause | R restart | Q quit',color(2))
  put(s,h-1,2,'Line a gap under the ball before it lands. X tiles end the run.',color(4));s.refresh()
if __name__=='__main__':
 if '--version' in sys.argv:print(VERSION)
 else:raise SystemExit(run(play))
