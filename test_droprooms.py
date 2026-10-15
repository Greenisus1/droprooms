import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import droprooms as a

class Tests(unittest.TestCase):
 def mk(self,seed=1,level=1):return a.Tower(seed=seed,level=level)
 def test_initial(self):
  g=self.mk();self.assertEqual(g.score,0);self.assertEqual(g.level,1);self.assertFalse(g.over);self.assertEqual(len(g.floors),a.FLOORS_PER_LEVEL)
 def test_angle_in(self):
  g=self.mk();self.assertTrue(g.angle_in(100,100,40));self.assertTrue(g.angle_in(10,350,40));self.assertFalse(g.angle_in(50,100,40))
 def test_segment_gap(self):
  g=self.mk();f={'gap':100,'gw':60,'danger':[]}
  self.assertEqual(g.segment_at(f,100),'gap');self.assertEqual(g.segment_at(f,131),'solid')
 def test_segment_danger(self):
  g=self.mk();f={'gap':100,'gw':60,'danger':[(200,40)]}
  self.assertEqual(g.segment_at(f,200),'danger');self.assertEqual(g.segment_at(f,179),'solid');self.assertEqual(g.segment_at(f,221),'solid')
 def test_gap_wrap(self):
  g=self.mk();f={'gap':350,'gw':40,'danger':[]}
  self.assertEqual(g.segment_at(f,10),'gap');self.assertEqual(g.segment_at(f,325),'solid')
 def test_land_gap(self):
  g=self.mk(2);g.rot=(-g.floors[0]['gap'])%360
  self.assertEqual(g.land(),'gap');self.assertFalse(g.over)
 def test_land_danger(self):
  g=self.mk(3);g.rot=(-g.floors[0]['danger'][0][0])%360
  self.assertEqual(g.land(),'danger');self.assertTrue(g.over)
 def test_land_solid(self):
  g=self.mk(3);g.rot=(-(g.floors[0]['gap']+180))%360
  self.assertEqual(g.land(),'solid');self.assertFalse(g.over)
 def test_drop_scores(self):
  g=self.mk(2);g.drop()
  self.assertEqual(g.index,1);self.assertEqual(g.score,1);self.assertEqual(g.drops,1);self.assertEqual(len(g.floors),a.FLOORS_PER_LEVEL+1)
 def test_level_up(self):
  g=self.mk(2)
  for _ in range(a.FLOORS_PER_LEVEL):
   g.rot=(-g.floors[g.index]['gap'])%360;self.assertEqual(g.land(),'gap');g.drop()
  self.assertEqual(g.level,2);self.assertEqual(g.score,a.FLOORS_PER_LEVEL+10)
 def test_gap_shrinks(self):
  self.assertGreater(a.Tower(seed=1,level=1).gap_width(),a.Tower(seed=1,level=5).gap_width())
 def test_danger_grows(self):
  self.assertLess(a.Tower(seed=1,level=1).danger_count(),a.Tower(seed=1,level=5).danger_count())
 def test_danger_avoids_gap(self):
  g=self.mk(9)
  for f in g.floors:
   for start,width in f['danger']:
    half=f['gw']/2+width/2
    self.assertGreater(abs(((start-f['gap']+180)%360)-180),half-0.001)
 def test_rotate_wraps(self):
  g=self.mk();g.rotate(1,1);self.assertAlmostEqual(g.rot,160.);g.rotate(1.5,-1);self.assertAlmostEqual(g.rot,(160-240)%360)
 def test_deterministic(self):
  a1=self.mk(42);a2=self.mk(42)
  self.assertEqual([f['gap'] for f in a1.floors],[f['gap'] for f in a2.floors])
 def test_record(self):
  with tempfile.TemporaryDirectory() as d,patch.object(a,'RECORD',Path(d)/'best.json'):
   self.assertTrue(a.save(50));a.save(2);self.assertEqual(a.best(),50)
if __name__=='__main__':unittest.main()
