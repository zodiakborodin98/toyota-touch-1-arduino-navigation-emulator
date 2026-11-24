#!/usr/bin/env python3
"""Compare the published TAS300 map with the host menu handler, offline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
from source_menu import source_menu_target


def check_menu(zones):
    expected = {}
    for action, zone in zones.items():
        x_min, x_max, y_min, y_max = zone["raw_bounds"]
        if not (0 <= x_min <= x_max <= 255 and 0 <= y_min <= y_max <= 255):
            raise ValueError(f"{action}: bounds are outside the raw touchscreen")
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if (x, y) in expected:
                    raise ValueError(f"{action}: overlap at {(x, y)}")
                expected[x, y] = action
    for x in range(256):
        for y in range(256):
            actual = source_menu_target(x, y)
            if actual != expected.get((x, y)):
                raise ValueError(f"({x}, {y}): menu returns {actual}, map lists {expected.get((x, y))}")


def check_points(points):
    # Examples taken from five independently marked touch locations.
    # Values are raw bytes and nearest pixels on the full 480 x 240 surface.
    reference = {
        "top_left": ((16, 239), (30, 15)),
        "top_right": ((233, 219), (438, 34)),
        "bottom_left": ((19, 15), (36, 225)),
        "bottom_right": ((237, 35), (445, 206)),
        "center": ((115, 126), (216, 121)),
    }
    for location, ((x, y), pixel) in reference.items():
        if len(points[location]) != 5 or [x, y] not in points[location]:
            raise ValueError(f"{location}: recorded sample missing")
        linux_x, linux_y = x * 257, (255 - y) * 257
        projected = (round(linux_x * 479 / 65535), round(linux_y * 239 / 65535))
        if projected != pixel:
            raise ValueError(f"{location}: projected {projected}, expected {pixel}")


if __name__ == "__main__":
    data = json.loads((ROOT / "maps" / "tas300.json").read_text(encoding="utf-8"))
    check_menu(data["menu_source"]["zones"])
    check_points(data["observed_taps_raw_xy"])
    print("OK: 65536 menu coordinates and five measured reference points")
