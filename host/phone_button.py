"""Observed TAS300 B2/85 button events; no assumptions about other devices."""
import re

FRAME = re.compile(rb'^TIRTA_RX D 120 -> 122 C=F N=10 DATA=00 25 B2 85 ((?:[0-9A-F]{2}(?: |$)){12})$')

class PhoneButton:
    def __init__(self):
        self.phone_down = False
        self.map_down = False

    def feed(self, line):
        match = FRAME.match(line.rstrip(b'\r\n'))
        if not match:
            return None
        data = bytes.fromhex(match.group(1).decode('ascii'))
        phone, map_key = bool(data[0] & 4), bool(data[0] & 2)
        event = 'phone' if phone and not self.phone_down else 'map' if map_key and not self.map_down else None
        self.phone_down, self.map_down = phone, map_key
        return event
