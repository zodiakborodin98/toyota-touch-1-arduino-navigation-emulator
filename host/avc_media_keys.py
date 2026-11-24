"""Measured TAS300 track-button edges in directed D4/84 messages."""
import re

FRAME = re.compile(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 25 D4 84 ([0-9A-F]{2}) ([0-9A-F]{2})$')


class TrackButtons:
    def __init__(self):
        self.down = 0

    def feed(self, line):
        m = FRAME.match(line.rstrip(b'\r\n'))
        if not m:
            return ()
        current = int(m.group(1), 16) & 0xC0
        rising = current & ~self.down
        self.down = current
        return tuple(name for bit, name in ((0x80, 'next'), (0x40, 'previous')) if rising & bit)


class LiviRestartButton:
    """Recognize the measured 0x01 key once for each press."""
    def __init__(self):
        self.down = False

    def feed(self, line):
        m = FRAME.match(line.rstrip(b'\r\n'))
        if not m:
            return False
        down = bool(int(m.group(1), 16) & 0x01)
        pressed = down and not self.down
        self.down = down
        return pressed


class AudioPowerEvents:
    """Interpret D4 on/off transitions after initial sync and source selection."""
    def __init__(self):
        self.state = None
        self.suppressed_until = 0.0

    def suppress_source_change(self, now):
        self.suppressed_until = now + 3.0

    def update(self, enabled, video_active, overlay_active, now):
        previous = self.state
        self.state = enabled
        if (previous is None or previous == enabled or not video_active or overlay_active
                or now < self.suppressed_until):
            return None
        return 'audio_play' if enabled else 'audio_pause'
