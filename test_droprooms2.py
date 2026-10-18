import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, '/tmp')
import droprooms2 as a

def ballish(rows):
    out = []
    for r, row in enumerate(rows):
        for i, c in enumerate(row):
            if (c >> 16) > 150 and ((c >> 8) & 255) > 130 and (c & 255) > 100 and (c >> 16) - (c & 255) > 20:
                out.append((r, i))
    return out

class TowerTests(unittest.TestCase):
    def mk(self, seed=1, level=1): return a.Tower(seed=seed, level=level)
    def test_initial(self):
        g = self.mk(); self.assertEqual(g.score, 0); self.assertEqual(g.level, 1)
        self.assertFalse(g.over); self.assertEqual(len(g.floors), a.FLOORS_PER_LEVEL)
    def test_angle_in(self):
        g = self.mk()
        self.assertTrue(g.angle_in(100, 100, 40)); self.assertTrue(g.angle_in(10, 350, 40))
        self.assertFalse(g.angle_in(50, 100, 40))
    def test_segment_gap(self):
        g = self.mk(); f = {'gap': 100, 'gw': 60, 'danger': []}
        self.assertEqual(g.segment_at(f, 100), 'gap'); self.assertEqual(g.segment_at(f, 131), 'solid')
    def test_segment_danger(self):
        g = self.mk(); f = {'gap': 100, 'gw': 60, 'danger': [(200, 40)]}
        self.assertEqual(g.segment_at(f, 200), 'danger')
        self.assertEqual(g.segment_at(f, 179), 'solid'); self.assertEqual(g.segment_at(f, 221), 'solid')
    def test_gap_wrap(self):
        g = self.mk(); f = {'gap': 350, 'gw': 40, 'danger': []}
        self.assertEqual(g.segment_at(f, 10), 'gap'); self.assertEqual(g.segment_at(f, 325), 'solid')
    def test_land_gap(self):
        g = self.mk(2); g.rot = (-g.floors[0]['gap']) % 360
        self.assertEqual(g.land(), 'gap'); self.assertFalse(g.over)
    def test_land_danger(self):
        g = self.mk(3); g.rot = (-g.floors[0]['danger'][0][0]) % 360
        self.assertEqual(g.land(), 'danger'); self.assertTrue(g.over)
    def test_land_solid(self):
        g = self.mk(3); g.rot = (-(g.floors[0]['gap'] + 180)) % 360
        self.assertEqual(g.land(), 'solid'); self.assertFalse(g.over)
    def test_drop_scores(self):
        g = self.mk(2); g.drop()
        self.assertEqual(g.index, 1); self.assertEqual(g.score, 1); self.assertEqual(g.drops, 1)
        self.assertEqual(len(g.floors), a.FLOORS_PER_LEVEL + 1)
    def test_level_up(self):
        g = self.mk(2)
        for _ in range(a.FLOORS_PER_LEVEL):
            g.rot = (-g.floors[g.index]['gap']) % 360
            self.assertEqual(g.land(), 'gap'); g.drop()
        self.assertEqual(g.level, 2); self.assertEqual(g.score, a.FLOORS_PER_LEVEL + 10)
    def test_gap_shrinks(self):
        self.assertGreater(a.Tower(seed=1, level=1).gap_width(), a.Tower(seed=1, level=5).gap_width())
    def test_danger_grows(self):
        self.assertLess(a.Tower(seed=1, level=1).danger_count(), a.Tower(seed=1, level=5).danger_count())
    def test_danger_avoids_gap(self):
        g = self.mk(9)
        for f in g.floors:
            for start, width in f['danger']:
                half = f['gw'] / 2 + width / 2
                self.assertGreater(abs(((start - f['gap'] + 180) % 360) - 180), half - 0.001)
    def test_rotate_wraps(self):
        g = self.mk(); g.rotate(1, 1); self.assertAlmostEqual(g.rot, 160.)
        g.rotate(1.5, -1); self.assertAlmostEqual(g.rot, (160 - 240) % 360)
    def test_deterministic(self):
        a1 = self.mk(42); a2 = self.mk(42)
        self.assertEqual([f['gap'] for f in a1.floors], [f['gap'] for f in a2.floors])
    def test_record(self):
        with tempfile.TemporaryDirectory() as d, patch.object(a, 'RECORD', Path(d) / 'best.json'):
            self.assertTrue(a.save(50)); a.save(2); self.assertEqual(a.best(), 50)

class RenderTests(unittest.TestCase):
    def test_frame_shape(self):
        rows = a.Scene().render(self.tw(), 60, 40, 0.5, 1.0)
        self.assertEqual(len(rows), 40)
        for r in rows: self.assertEqual(len(r), 60)
    def tw(self, seed=3): return a.Tower(seed=seed)
    def test_ball_visible_full_bounce(self):
        tw = self.tw(); sc = a.Scene()
        for by in (0.34, 0.6, 0.96):
            for rot in (0.0, 1.5, 3.0, 4.5):
                cells = ballish(sc.render(tw, 50, 78, by, rot))
                self.assertGreater(len(cells), 10, f"ball missing y={by} rot={rot}")
    def test_ball_front_of_column(self):
        # ball must render at screen center over the column (not hidden behind it)
        tw = self.tw(); sc = a.Scene()
        cells = ballish(sc.render(tw, 78, 50, 0.6, 0.0))
        ys = [r for r, i in cells]; xs = [i for r, i in cells]
        self.assertLess(abs((max(xs) + min(xs)) / 2 - 39), 8)
    def test_fov_cycle_changes_frame(self):
        tw = self.tw(); sc = a.Scene()
        a1 = sc.render(tw, 40, 60, 0.6, 0.0)
        sc.set_fov(90.0)
        a2 = sc.render(tw, 40, 60, 0.6, 0.0)
        self.assertNotEqual(a1, a2)
    def test_column_and_floors_render(self):
        rows = a.Scene().render(self.tw(), 50, 78, 0.6, 0.0)
        distinct = len({c for row in rows for c in row})
        self.assertGreater(distinct, 30)  # shaded 3D scene, not a flat fill

if __name__ == '__main__': unittest.main()
