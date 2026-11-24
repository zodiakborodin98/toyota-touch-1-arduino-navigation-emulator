"""Decode measured source-button events and map raw touch positions."""
from phone_button import FRAME


class SourceButton:
    def __init__(self):
        self.down = False

    def feed(self, line):
        match = FRAME.match(line.rstrip(b'\r\n'))
        if not match:
            return False
        data = bytes.fromhex(match.group(1).decode('ascii'))
        current = bool(data[-1] & 0x80)
        triggered = current and not self.down
        self.down = current
        return triggered


class MediaButton:
    def __init__(self):
        self.down = False

    def feed(self, line):
        match = FRAME.match(line.rstrip(b'\r\n'))
        if not match:
            return False
        data = bytes.fromhex(match.group(1).decode('ascii'))
        current = bool(data[0] & 0x01)
        triggered = current and not self.down
        self.down = current
        return triggered


def source_menu_target(x, y):
    # Screen is 480x234; coordinates come as 0..255 with inverted Y.
    if 186 <= x <= 249 and 214 <= y <= 249:
        return 'back'
    columns = ((4, 82), (87, 165), (170, 248))
    for index, (low, high) in enumerate(columns):
        if low <= x <= high:
            if 154 <= y <= 205:
                return ('fm', 'am', 'cd')[index]
            if 93 <= y <= 144:
                return ('aux', 'external', None)[index]
    return None
