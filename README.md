# Droprooms

A fullscreen, offline faux-3D helix tower dropper for Raspberry Pi and Linux terminals, dressed in a flickering backrooms mood. A ball bounces on a rotating ring tower; you rotate the tower to line up the gap before the ball lands. Pass a floor, score a point. Land on an X tile and the run sizzles out. Clear 12 floors to level up - gaps shrink and bad tiles multiply.

Original name, art, and code, in the spirit of rotating-tower droppers like Helix Jump. This is a simplified terminal tribute: it shares no assets or code with any commercial game and does not claim to be a port.

## Run

```
python3 droprooms.py
```

Python 3 with curses. No other dependencies, no network, no install. Saves your best score to `~/.local/share/droprooms/best.json`.

## Controls

- **Left / Right or A / D** - rotate the tower
- **P** - pause
- **R** - restart
- **Q / Esc** - quit

## Scoring

- Floor passed: +1
- Level up (12 floors): +10, smaller gaps, more bad tiles

## Install from the Pi App Store

Search for `droprooms` in the games category, or use `app-store.sh` directly:

```
bash app-store.sh INSTALL
bash app-store.sh StAtUs
bash app-store.sh RUN
```

## Tests

```
python3 test_droprooms.py   # 16 unit tests
python3 test_terminal.py    # real PTY controls/resize/restore check
```

## Scope

Local unit and PTY tests cover ring arc math with wraparound, gap/danger/solid detection, landing outcomes, scoring, level progression, shrinking gaps and growing danger, danger arcs avoiding the gap, rotation wrapping, deterministic seeds, best-score saves, resizing and clean terminal exit. Before publication, all 16 unit tests and the PTY control/resize/exit checks passed on a real aarch64 Raspberry Pi.

MIT licensed (Greenisus1).
