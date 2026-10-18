#!/usr/bin/env python3
"""droprooms2.py - DROPROOMS in first-person-ish terminal 3D.

Same tower-drop rules as droprooms.py (line a gap under the bouncing ball,
bad tiles end the run), rendered as an analytic low-poly 3D scene: central
column, ring floors with gaps and danger arcs, bouncing ball, backrooms
walls. Truecolor half-block cells, delta frames, non-blocking writes and
frame skip, same pipeline as maze2.py. Python standard library only.
"""
import argparse, math, os, random, select, shutil, sys, termios, time, tty
import json
from itertools import groupby
from pathlib import Path

VERSION = '2.0.0'
RECORD = Path.home() / '.local/share/droprooms' / 'best.json'
HALF = "▀"

# --------------------------------------------------------------------------
# Tower mechanics (identical rules to droprooms.py 1.0.0)
# --------------------------------------------------------------------------
FLOORS_PER_LEVEL = 12


class Tower:
    def __init__(self, seed=None, level=1):
        self.rng = random.Random(seed); self.level = level; self.rot = 0.; self.index = 0
        self.score = 0; self.over = False; self.scroll = 0.; self.drops = 0
        self.message = 'Left/Right rotates the tower. Drop the ball through the gaps!'
        self.floors = []; self.extend(FLOORS_PER_LEVEL)

    def gap_width(self): return max(50, 110 - 8 * self.level)
    def danger_count(self): return min(4, self.level)

    def extend(self, n):
        for _ in range(n):
            gap = self.rng.uniform(0, 360); arcs = []
            for _ in range(self.danger_count()):
                while True:
                    start = self.rng.uniform(0, 360); width = self.rng.uniform(20, 45)
                    a = (start - gap) % 360
                    if a > self.gap_width() / 2 + width and 360 - a > self.gap_width() / 2 + width: break
                arcs.append((start, width))
            self.floors.append({'gap': gap, 'gw': self.gap_width(), 'danger': arcs})

    def angle_in(self, ang, start, width):
        return abs(((ang - start + 180) % 360) - 180) <= width / 2 if width < 360 else True

    def segment_at(self, floor, ang):
        a = ang % 360
        if self.angle_in(a, floor['gap'], floor['gw']): return 'gap'
        for start, width in floor['danger']:
            if self.angle_in(a, start, width): return 'danger'
        return 'solid'

    def rotate(self, dt, dirn): self.rot = (self.rot + dirn * 160 * dt) % 360
    def ball_angle(self): return (-self.rot) % 360

    def land(self):
        seg = self.segment_at(self.floors[self.index], self.ball_angle())
        if seg == 'danger':
            self.over = True; self.message = 'Sizzled on a bad tile. R restarts.'
        return seg

    def drop(self):
        self.index += 1; self.score += 1; self.scroll = 1.; self.drops += 1
        if self.drops % FLOORS_PER_LEVEL == 0:
            self.level += 1; self.score += 10
            self.message = 'Level ' + str(self.level) + '! Gaps shrink, bad tiles grow.'
        self.extend(1)

    def tick(self, dt):
        self.scroll = max(0., self.scroll - dt * 4)


def best():
    try:
        if RECORD.is_symlink(): return 0
        return max(0, int(json.loads(RECORD.read_text()).get('best', 0)))
    except (OSError, ValueError, TypeError, AttributeError): return 0


def save(score):
    try:
        if any(p.is_symlink() for p in [RECORD, *RECORD.parents]): return False
        RECORD.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = RECORD.with_suffix('.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as f: json.dump({'best': max(score, best())}, f)
        tmp.replace(RECORD); return True
    except OSError: return False


# --------------------------------------------------------------------------
# Color + frame pipeline (same approach as maze2.py)
# --------------------------------------------------------------------------
def pack(c):
    return (c[0] << 16) | (c[1] << 8) | c[2]


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


P16 = [(0,0,0),(128,0,0),(0,128,0),(128,128,0),(0,0,128),(128,0,128),(0,128,128),(192,192,192),
       (128,128,128),(255,0,0),(0,255,0),(255,255,0),(0,0,255),(255,0,255),(0,255,255),(255,255,255)]


def make_color(mode):
    fc, bc = {}, {}
    if mode == "true":
        def fg(c):
            s = fc.get(c)
            if s is None: s = fc[c] = "\x1b[38;2;%d;%d;%dm" % (c >> 16, (c >> 8) & 255, c & 255)
            return s
        def bg(c):
            s = bc.get(c)
            if s is None: s = bc[c] = "\x1b[48;2;%d;%d;%dm" % (c >> 16, (c >> 8) & 255, c & 255)
            return s
    elif mode == "256":
        def idx(c):
            r, g, b = c >> 16, (c >> 8) & 255, c & 255
            return 16 + 36 * min(5, round(r / 51)) + 6 * min(5, round(g / 51)) + min(5, round(b / 51))
        def fg(c):
            s = fc.get(c)
            if s is None: s = fc[c] = "\x1b[38;5;%dm" % idx(c)
            return s
        def bg(c):
            s = bc.get(c)
            if s is None: s = bc[c] = "\x1b[48;5;%dm" % idx(c)
            return s
    else:
        def near(c):
            r, g, b = c >> 16, (c >> 8) & 255, c & 255
            return min(range(16), key=lambda i: 2*(r-P16[i][0])**2 + 4*(g-P16[i][1])**2 + 3*(b-P16[i][2])**2)
        def fg(c):
            s = fc.get(c)
            if s is None:
                i = near(c); s = fc[c] = "\x1b[%dm" % (30 + i if i < 8 else 90 + i - 8)
            return s
        def bg(c):
            s = bc.get(c)
            if s is None:
                i = near(c); s = bc[c] = "\x1b[%dm" % (40 + i if i < 8 else 100 + i - 8)
            return s
    return fg, bg


def detect_colors(choice):
    if choice != "auto": return choice
    ct = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "")
    if "truecolor" in ct or "24bit" in ct: return "true"
    if term == "linux": return "16"
    return "256"


HUDBG = (24, 22, 28)


def hud_cells(width, left, right):
    cells = []
    for txt, colr in left:
        for ch in txt: cells.append((pack(colr), pack(HUDBG), ch))
    rcells = []
    for txt, colr in right:
        for ch in txt: rcells.append((pack(colr), pack(HUDBG), ch))
    pad = width - len(cells) - len(rcells)
    if pad < 1:
        rcells = []; pad = width - len(cells)
    cells += [(0, pack(HUDBG), " ")] * max(0, pad) + rcells
    return cells[:width]


def present(vr, W, rows, rowmap, hud, fg, bg, prev=None):
    cur = []
    for r in range(vr):
        cells = [(t, b, HALF) for t, b in zip(rows[2 * r], rows[2 * r + 1])]
        ov = rowmap.get(r)
        if ov:
            for c, v in ov.items():
                if 0 <= c < W: cells[c] = v
        cur.append(cells)
    cur.append(list(hud))
    parts = []
    if prev is None or len(prev) != len(cur) or any(len(a) != len(b) for a, b in zip(prev, cur)):
        spans = [((r, 0), (r, len(cur[r]) - 1)) for r in range(len(cur)) if cur[r]]
    else:
        spans = []
        for r in range(len(cur)):
            a, b = prev[r], cur[r]
            c = 0; n = len(b)
            while c < n:
                if a[c] != b[c]:
                    c0 = c
                    while c < n and a[c] != b[c]: c += 1
                    spans.append(((r, c0), (r, c - 1)))
                else:
                    c += 1
    pf = pb = -1
    for (r, c0), (r2, c1) in spans:
        parts.append("\x1b[%d;%dH" % (r + 1, c0 + 1))
        for key, grp in groupby(cur[r][c0:c1 + 1]):
            cnt = sum(1 for _ in grp)
            if key[0] != pf: parts.append(fg(key[0])); pf = key[0]
            if key[1] != pb: parts.append(bg(key[1])); pb = key[1]
            parts.append(key[2] * cnt)
    parts.append("\x1b[0m")
    return "".join(parts), cur


def text_box(lines, W, vr):
    """Centered overlay; returns rowmap {(r,c):(fg,bg,ch)}."""
    width = max(len(t) for t, _ in lines) + 6
    height = len(lines) + 4
    x0 = max(0, (W - width) // 2); y0 = max(0, (vr - height) // 2)
    rm = {}
    border = (pack((150, 130, 200)), pack((30, 28, 36)))
    for i in range(width):
        rm[(y0, x0 + i)] = border + ("-",)
        rm[(y0 + height - 1, x0 + i)] = border + ("-",)
    for j in range(height):
        rm[(y0 + j, x0)] = border + ("|",)
        rm[(y0 + j, x0 + width - 1)] = border + ("|",)
    for j in range(1, height - 1):
        for i in range(1, width - 1):
            rm[(y0 + j, x0 + i)] = (0, pack((30, 28, 36)), " ")
    for j, (txt, colr) in enumerate(lines):
        for i, ch in enumerate(txt):
            rm[(y0 + 2 + j, x0 + 3 + i)] = (pack(colr), pack((30, 28, 36)), ch)
    return rm


# --------------------------------------------------------------------------
# Input (from maze2.py)
# --------------------------------------------------------------------------
ARROWS = {0x41: "up", 0x42: "down", 0x43: "right", 0x44: "left"}


def parse(buf):
    ev, i, n = [], 0, len(buf)
    while i < n:
        b = buf[i]
        if b != 0x1B:
            ev.append(("key", chr(b).lower())); i += 1; continue
        if i + 1 >= n:
            ev.append(("esc",)); i += 1; continue
        nxt = buf[i + 1]
        if nxt in (0x5B, 0x4F):
            j = i + 2
            while j < n and 48 <= buf[j] <= 59: j += 1
            if j >= n: break
            if buf[j] in ARROWS: ev.append(("arrow", ARROWS[buf[j]]))
            i = j + 1; continue
        i += 2
    return ev, buf[i:]


def _sleep(fd, secs):
    end = time.time() + max(0.0, secs)
    got = b""
    while True:
        rem = max(0.0, end - time.time())
        if select.select([fd], [], [], rem)[0]:
            try: got += os.read(fd, 4096)
            except OSError: pass
        if time.time() >= end: break
    return got


# --------------------------------------------------------------------------
# 3D scene
# --------------------------------------------------------------------------
RC = 0.52            # central column radius
RP = 1.65            # platform ring outer radius
FH = 1.02            # floor spacing
VISIBLE = 6          # floors rendered below the ball
FOG = (54, 47, 36)   # backrooms haze
WALL = (188, 165, 96)
CARPET = (148, 121, 66)
CARPET_D = (118, 95, 50)
DANGER = (205, 64, 42)
BALL = (250, 240, 215)
CEIL = (166, 148, 88)
LX, LY, LZ = -0.42, 0.82, -0.38   # light direction (unnormalized ok, normalized below)
_ln = math.sqrt(LX * LX + LY * LY + LZ * LZ)
LX, LY, LZ = LX / _ln, LY / _ln, LZ / _ln


class Scene:
    """Camera fixed behind the ball; tower rotates under it (angle -rot)."""

    def __init__(self, fov=62.0):
        self.set_fov(fov)

    def set_fov(self, fov):
        self.fov = fov
        self.scale = math.tan(math.radians(fov) / 2)

    def render(self, tw, W, PH, ball_y, flick):
        """Returns rows[PH][W] of packed colors. tw = Tower."""
        # camera: at (0, ch, cd) looking at (0, 0.35, 0)
        ch, cd = 2.35, -5.6
        tx, ty, tz = 0.0, 0.35 - ch, 0.0 - cd
        tl = math.sqrt(tx * tx + ty * ty + tz * tz)
        fx, fy, fz = tx / tl, ty / tl, tz / tl          # forward
        rx, ry, rz = fz, 0.0, -fx                        # right = f x up(0,1,0)... (fx,0,fz)x(0,1,0) = (0*0-fz*1, fz*0-fx*0, fx*1-0) = (-fz,0,fx)
        rx, ry, rz = -fz, 0.0, fx
        ux, uy, uz = ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx
        aspect = W / max(1, PH)
        floors = []
        for slot in range(VISIBLE):
            fi = tw.index + slot
            if fi >= len(tw.floors): break
            fy_i = -slot * FH + tw.scroll * FH
            floors.append((fy_i, tw.floors[fi]))
        rows = []
        invph = 2.0 / PH
        for py in range(PH):
            ny = (1.0 - (py + 0.5) * invph) * self.scale
            dy = fy + ny * uy
            row = []
            # per-row plane hits: t = (plane_y - ch) / dy (same for all columns)
            plane_ts = [((y - ch) / dy, fl) if dy < -1e-6 else (None, fl) for y, fl in floors]
            # room shell planes
            t_roomfloor = (-6.3 - ch) / dy if dy < -1e-6 else None
            for px in range(W):
                nx = ((px + 0.5) * 2.0 / W - 1.0) * self.scale * aspect
                dx = fx + nx * rx + ny * ux
                dy2 = fy + nx * ry + ny * uy
                dz = fz + nx * rz + ny * uz
                best_t, shade = 1e9, None
                # ball sphere at (0, ball_y, RP + 0.30)
                br = 0.34
                ocx, ocy, ocz = 0.0, ch - ball_y, cd + (RP + 0.30)
                qa = dx * dx + dy2 * dy2 + dz * dz
                qb = 2 * (ocx * dx + ocy * dy2 + ocz * dz)
                qc = ocx * ocx + ocy * ocy + ocz * ocz - br * br
                disc = qb * qb - 4 * qa * qc
                if disc > 0:
                    t = (-qb - math.sqrt(disc)) / (2 * qa)
                    if 0.01 < t < best_t:
                        hx, hy, hz = ocx + t * dx, ocy + t * dy2, ocz + t * dz
                        nl = math.sqrt(hx * hx + hy * hy + hz * hz) or 1
                        diff = max(0.0, (hx * LX + hy * LY + hz * LZ) / nl)
                        shade = mix((150, 120, 90), BALL, 0.35 + 0.65 * diff)
                        best_t = t
                # central column x^2+z^2=RC^2
                qa2 = dx * dx + dz * dz
                if qa2 > 1e-9:
                    qb2 = 2 * (0 * dx + cd * dz)
                    qc2 = cd * cd - RC * RC
                    disc2 = qb2 * qb2 - 4 * qa2 * qc2
                    if disc2 > 0:
                        t = (-qb2 - math.sqrt(disc2)) / (2 * qa2)
                        if 0.01 < t < best_t:
                            hy = ch + t * dy2
                            if hy > -6.3:
                                hx, hz = t * dx, cd + t * dz
                                nl = RC
                                diff = max(0.0, (hx * LX + hz * LZ) / nl)
                                stripe = 0.9 + 0.1 * math.sin(math.atan2(hx, hz) * 14)
                                base = mix(WALL, (150, 128, 70), min(1.0, max(0.0, -hy / 6.5)))
                                shade = (int(base[0] * (0.45 + 0.55 * diff) * stripe),
                                         int(base[1] * (0.45 + 0.55 * diff) * stripe),
                                         int(base[2] * (0.45 + 0.55 * diff) * stripe))
                                best_t = t
                # floors (ring slabs)
                for t_i, fl in plane_ts:
                    if t_i is None or t_i <= 0.01 or t_i >= best_t: continue
                    hx, hz = t_i * dx, cd + t_i * dz
                    rr = math.sqrt(hx * hx + hz * hz)
                    if RC + 0.015 <= rr <= RP:
                        ang = math.degrees(math.atan2(hx, -hz)) % 360
                        seg = tw.segment_at(fl, (ang - tw.rot) % 360)
                        if seg == 'gap': continue
                        diff = max(0.0, LY)  # top surface, constant-ish
                        edge = 1.0 if rr > RP - 0.07 or rr < RC + 0.09 else 0.0
                        base = DANGER if seg == 'danger' else mix(CARPET, CARPET_D, (rr - RC) / (RP - RC))
                        k = (0.5 + 0.5 * diff) * (1.0 - 0.25 * edge)
                        shade = (int(base[0] * k), int(base[1] * k), int(base[2] * k))
                        best_t = t_i
                # room shell: floor then back wall
                if t_roomfloor is not None and t_roomfloor > 0.01 and t_roomfloor < best_t:
                    hx, hz = t_roomfloor * dx, cd + t_roomfloor * dz
                    if abs(hx) < 14 and hz < 11:
                        k = 0.55 + 0.2 * math.sin(hx * 0.8) * math.sin(hz * 0.8)
                        shade = (int(96 * k + 40), int(80 * k + 34), int(46 * k + 22))
                        best_t = t_roomfloor
                if shade is None:
                    # back wall / ceiling gradient
                    if dz > 1e-6:
                        t_w = (10.5 - cd) / dz
                        hy = ch + t_w * dy2
                        grad = min(1.0, max(0.0, (hy + 6.3) / 10.5))
                        base = mix((86, 72, 44), CEIL, grad)
                    else:
                        base = (70, 60, 40)
                    # fluorescent flicker band near ceiling
                    if ny > 0.55 and flick > 0.12:
                        base = mix(base, (255, 250, 220), 0.5)
                    shade = base
                    best_t = 60.0
                fogk = min(1.0, best_t / 16.0)
                row.append(pack(mix(shade, FOG, fogk * fogk * 0.85)))
            rows.append(row)
        return rows


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def play(args):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    fg, bg = make_color(detect_colors(args.colors))
    out_fd = sys.stdout.buffer.fileno()
    os.set_blocking(out_fd, False)
    pending = b""

    def w(s, deadline=3.0):
        data = s.encode("utf-8")
        end = time.time() + deadline
        while data and time.time() < end:
            try:
                n = os.write(out_fd, data); data = data[n:]
            except BlockingIOError:
                select.select([], [out_fd], [], min(0.25, max(0.0, end - time.time())))
            except OSError:
                return

    def pump():
        nonlocal pending
        while pending:
            try:
                n = os.write(out_fd, pending); pending = pending[n:]
            except BlockingIOError:
                return False
            except OSError:
                pending = b""; return False
        return True

    tw = Tower(seed=args.seed)
    scene = Scene()
    state = "title"
    buf = b""
    frame = 1.0 / max(5, args.fps)
    rx = 2 if args.fast else 1
    ema = 0.0; good = 0.0; heal = 0; dropped = 0
    prev_cells = None
    last = time.time()
    bounce = 0.0
    dirn = 0
    paused = False
    recorded = False
    high = best()
    lastsize = None
    flick = 1.0
    try:
        tty.setcbreak(fd)
        w("\x1b[?1049h\x1b[?25l\x1b[2J")
        while True:
            fstart = time.time(); now = fstart
            dt = min(0.05, now - last); last = now
            events, buf = parse(buf)
            quit_ = False; started = False
            for e in events:
                kind = e[0]
                if kind == "esc": quit_ = True
                elif kind == "key":
                    k = e[1]
                    if k in ("x", "\x03", "q"): quit_ = True
                    elif k == "p" and state == "play": paused = not paused
                    elif k == "r":
                        tw = Tower(); recorded = False; paused = False; bounce = 0.0
                    elif k == "[" : scene.set_fov(max(40, scene.fov - 3))
                    elif k == "]": scene.set_fov(min(120, scene.fov + 3))
                    else:
                        if state == "title": started = True
                        if k == "a": dirn = -1
                        elif k == "d": dirn = 1
                elif kind == "arrow" and state == "play":
                    if e[1] == "left": dirn = -1
                    elif e[1] == "right": dirn = 1
            if quit_: break
            if started: state = "play"

            cols_t, rows_t = shutil.get_terminal_size((80, 24))
            if (cols_t, rows_t) != lastsize:
                lastsize = (cols_t, rows_t); prev_cells = None; w("\x1b[0m\x1b[2J")
            if cols_t < 44 or rows_t < 14:
                w("\x1b[H\x1b[0mTerminal too small - need at least 44x14.")
                buf += _sleep(fd, frame); continue
            W = cols_t; vr = rows_t - 1; PH = vr * 2

            if state == "play" and not tw.over and not paused:
                tw.rotate(dt, dirn); tw.tick(dt)
                bounce += dt * 3.2
                if bounce >= 1:
                    bounce = 0
                    seg = tw.land()
                    if seg == 'gap': tw.drop()
            dirn = 0 if not events else dirn
            if tw.over and not recorded:
                tw.message += ' Best saved.' if save(tw.score) else ' Save unavailable.'
                recorded = True; high = max(high, best())
            flick = tw.rng.random()

            ball_y = 0.34 + (1.0 - (2 * (bounce % 1) - 1) ** 2) * 0.62 if not tw.over else 0.34
            rows = scene.render(tw, W // rx if rx > 1 else W, PH, ball_y, flick)
            if rx > 1:
                rows = [[c for c in row for _ in range(rx)] for row in rows]
                rows = [row[:W] for row in rows]

            if state == "title":
                ov = text_box([
                    ("DROPROOMS 3D", (240, 230, 200)),
                    ("", (240, 230, 200)),
                    ("Line a gap under the ball.", (240, 230, 200)),
                    ("Bad tiles end the run.", (235, 120, 100)),
                    ("", (240, 230, 200)),
                    ("A/D or arrows  rotate tower", (200, 190, 230)),
                    ("[ ] FOV   P pause   R restart", (200, 190, 230)),
                    ("X quit", (200, 190, 230)),
                    ("", (240, 230, 200)),
                    ("press any key to start", (110, 165, 255)),
                ], W, vr)
            elif tw.over:
                ov = text_box([
                    ("SIZZLED!", (235, 120, 100)),
                    ("", (240, 230, 200)),
                    ("Score  %d" % tw.score, (240, 230, 200)),
                    ("Level  %d" % tw.level, (240, 230, 200)),
                    ("Best   %d" % high, (240, 230, 200)),
                    ("", (240, 230, 200)),
                    ("R  restart     X  quit", (110, 165, 255)),
                ], W, vr)
            else:
                ov = {}
            left = [(" DROPROOMS 3D ", (200, 190, 230)),
                    (" SCORE ", (200, 190, 230)), (str(tw.score), (255, 235, 80)),
                    ("  LEVEL ", (200, 190, 230)), (str(tw.level), (255, 120, 190))]
            if paused: left.append(("  PAUSED", (255, 235, 80)))
            if tw.message and state == "play": left.append(("  " + tw.message, (120, 235, 170)))
            right = [("A/D rotate  P pause  R restart  X quit ", (150, 140, 190))]
            if dropped:
                right = [("%dx%d skip%d " % (rx, vr, dropped), (150, 140, 190))] + right
            hud = hud_cells(cols_t, left, right)
            rowmap = {}
            from collections import defaultdict
            tmp = defaultdict(dict)
            for (r, c), v in ov.items(): tmp[r][c] = v
            rowmap = tmp

            pump(); heal += 1
            if pending:
                dropped += 1
            else:
                force_full = prev_cells is None or heal >= 100 or args.no_delta
                text, prev_cells = present(vr, W, rows, rowmap, hud, fg, bg,
                                           None if force_full else prev_cells)
                if force_full: heal = 0
                pending = text.encode("utf-8"); pump()
            spent = time.time() - fstart
            ema = spent if ema == 0 else ema * 0.9 + spent * 0.1
            if ema > frame * 1.15 and rx < 4:
                rx += 1; ema = 0.0; good = 0.0; prev_cells = None
            elif ema < frame * 0.55:
                good += frame
                if good > 3.0 and rx > 1:
                    rx -= 1; ema = 0.0; good = 0.0; prev_cells = None
            else:
                good = 0.0
            buf += _sleep(fd, frame - spent)
    finally:
        pending = b""
        w("\x1b[0m\x1b[?25h\x1b[?1049l")
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    ap = argparse.ArgumentParser(description="DROPROOMS 3D - terminal helix tower dropper")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--colors", choices=["auto", "true", "256", "16"], default="auto")
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--fast", action="store_true", help="start at half horizontal resolution")
    ap.add_argument("--no-delta", action="store_true")
    args = ap.parse_args()
    if '--version' in sys.argv:
        print(VERSION); return
    play(args)


if __name__ == '__main__':
    main()
