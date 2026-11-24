#!/usr/bin/env python3
"""Bench bridge from Tirta AVC-LAN serial logging to a Linux uinput touchscreen.

Requires Linux termios2 and access to the serial port and /dev/uinput.
Calibration defaults map the observed 8-bit X and inverted Y to screen edges;
this is experimental. A 00 00 00 00 payload is treated as release.
"""
import argparse
import fcntl
import os
from pathlib import Path
import re
import select
import signal
import struct
import subprocess
import sys
import time
from phone_button import PhoneButton
from source_menu import SourceButton, MediaButton, source_menu_target
from avc_media_keys import TrackButtons, AudioPowerEvents, LiviRestartButton

base = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--port', default='/dev/ttyUSB0')
parser.add_argument('--uinput', default='/dev/uinput')
parser.add_argument('--trace-control', action='store_true', help='log non-touch directed AVC-LAN frames')
parser.add_argument('--nano-command', choices=['STOP', 'GO'], help='send one command to the Nano at startup')
parser.add_argument('--source-image', default=str(base / 'source-menu.bmp'))
parser.add_argument('--source-renderer', default=str(base / 'source-menu-ui'))
parser.add_argument('--livi-keys', action='store_true', help='forward keys to local LIVI IPC protocol 11')
parser.add_argument('--livi-restart-service', metavar='UNIT', help='restart this kiosk service on the measured restart key')
args = parser.parse_args()
pattern = re.compile(rb'TIRTA_RX D 120 -> 122 C=F N=08 DATA=00 21 24 78 ([0-9A-F]{2}) ([0-9A-F]{2}) ([0-9A-F]{2}) ([0-9A-F]{2})$')
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT, BTN_TOUCH, ABS_X, ABS_Y = 0, 0x14a, 0, 1
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT = 0x40045564, 0x40045565, 0x40045567
UI_SET_PROPBIT, INPUT_PROP_DIRECT = 0x4004556e, 1
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
event = struct.Struct('@llHHi')
ui = None
serial = None
pressed = False
last = None
running = True
phone_button = PhoneButton()
source_button = SourceButton()
media_button = MediaButton()
track_buttons = TrackButtons()
audio_power = AudioPowerEvents()
restart_button = LiviRestartButton()
last_livi_restart = None
audio_external_active = False
video_external_active = False
livi_keys = None
overlay = None
overlay_touch = None
overlay_kind = None
display_retry_at = None

def start_livi_keys():
    global livi_keys
    if args.livi_keys and (livi_keys is None or livi_keys.poll() is not None):
        livi_keys = subprocess.Popen(
            [sys.executable, '-u', str(base / 'livi-key-bridge.py')],
            stdin=subprocess.PIPE, bufsize=0, start_new_session=True)

def send_livi_key(name):
    global livi_keys
    if not args.livi_keys:
        return
    try:
        start_livi_keys()
        livi_keys.stdin.write(('%s %.6f\n' % (name, time.monotonic())).encode('ascii'))
        print('LIVI_KEY_QUEUED ' + name, flush=True)
    except (BrokenPipeError, OSError) as exc:
        print('LIVI_KEY_FAILED %s %s' % (name, exc), flush=True)
        livi_keys = None

def overlay_active():
    return overlay is not None and overlay.poll() is None

def close_overlay():
    global overlay, overlay_touch, overlay_kind, display_retry_at
    if overlay_active():
        try:
            os.killpg(overlay.pid, signal.SIGTERM)
            overlay.wait(timeout=2)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(overlay.pid, signal.SIGKILL)
    overlay = None
    overlay_touch = None
    display_retry_at = None
    print('OVERLAY_CLOSED kind=' + str(overlay_kind), flush=True)
    overlay_kind = None

def request_overlay_display():
    global display_retry_at
    os.write(serial, b'DSP\n')
    display_retry_at = time.monotonic() + 1.2
    print('OVERLAY_DISPLAY_REQUEST', flush=True)

def source_highlight(target):
    if overlay_kind == 'source' and overlay_active() and overlay.stdin:
        try:
            overlay.stdin.write(((target or 'none') + '\n').encode('ascii'))
        except (BrokenPipeError, OSError):
            print('SOURCE_HIGHLIGHT_PIPE_CLOSED', flush=True)

def open_overlay():
    global overlay, overlay_kind, pressed, last
    if overlay_active():
        close_overlay()
    if pressed:
        emit(EV_KEY, BTN_TOUCH, 0); report()
        pressed = False; last = None
    # Ask the existing Nano firmware for the same display transition as MAP.
    request_overlay_display()
    overlay = subprocess.Popen([args.source_renderer, args.source_image], stdin=subprocess.PIPE,
                               bufsize=0, start_new_session=True)
    overlay_kind = 'source'
    print('OVERLAY_REQUESTED kind=source', flush=True)

def end(*_):
    global running
    running = False

def emit(typ, code, value):
    os.write(ui, event.pack(0, 0, typ, code, value))

def report():
    emit(EV_SYN, SYN_REPORT, 0)

try:
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, end)
    serial = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    # Linux asm-generic termios2: BOTHER permits the Nano's 250000 baud.
    state = bytearray(44)
    fcntl.ioctl(serial, 0x802c542a, state, True)  # TCGETS2
    flags = struct.unpack_from('=I', state, 8)[0]
    struct.pack_into('=I', state, 0, 0)   # input flags: raw
    struct.pack_into('=I', state, 4, 0)   # output flags: raw
    struct.pack_into('=I', state, 12, 0)  # local flags: raw
    # CBAUD, CSIZE, PARENB, CSTOPB -> BOTHER, CS8, CREAD, CLOCAL.
    struct.pack_into('=I', state, 8, (flags & ~(0x100f | 0x30 | 0x100 | 0x40)) | 0x1000 | 0x30 | 0x80 | 0x800)
    struct.pack_into('=II', state, 36, 250000, 250000)
    fcntl.ioctl(serial, 0x402c542b, state)  # TCSETS2
    if args.nano_command:
        # Opening a second descriptor while the service owns the port does not
        # necessarily reset Nano, so give the active firmware time to read.
        time.sleep(0.25)
        os.write(serial, (args.nano_command + '\n').encode('ascii'))
    ui = os.open(args.uinput, os.O_WRONLY | os.O_NONBLOCK)
    for bit in (EV_SYN, EV_KEY, EV_ABS):
        fcntl.ioctl(ui, UI_SET_EVBIT, bit)
    fcntl.ioctl(ui, UI_SET_KEYBIT, BTN_TOUCH)
    for bit in (ABS_X, ABS_Y):
        fcntl.ioctl(ui, UI_SET_ABSBIT, bit)
    fcntl.ioctl(ui, UI_SET_PROPBIT, INPUT_PROP_DIRECT)
    # uinput_user_dev legacy ABI, with unsigned USB-like ID and abs ranges.
    absmax, absmin, absfuzz, absflat = ([0] * 64 for _ in range(4))
    absmax[ABS_X] = absmax[ABS_Y] = 65535
    device = struct.pack('@80sHHHHI256i', b'Toyota AVC-LAN Touch', 0x03, 0x1209, 0x0122, 1, 0,
                         *(absmax + absmin + absfuzz + absflat))
    os.write(ui, device)
    fcntl.ioctl(ui, UI_DEV_CREATE)
    print('READY port=' + args.port, flush=True)
    try:
        start_livi_keys()
    except OSError as exc:
        print('LIVI_KEYS_START_FAILED ' + str(exc), flush=True)
    buf = bytearray()
    while running:
        if display_retry_at is not None and time.monotonic() >= display_retry_at:
            display_retry_at = None
            if overlay_active():
                os.write(serial, b'DSP\n')
                print('OVERLAY_DISPLAY_RETRY once', flush=True)
        readable, _, _ = select.select([serial], [], [], 0.5)
        if not readable:
            continue
        chunk = os.read(serial, 4096)
        if not chunk:
            raise EOFError('serial disconnected')
        buf.extend(chunk)
        while b'\n' in buf:
            line, _, tail = buf.partition(b'\n')
            buf = bytearray(tail)
            clean = line.rstrip(b'\r')
            video_state = re.match(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 [0-9A-F]{2} B2 (42|43) ([0-9A-F]{2}) [0-9A-F]{2}$', clean)
            if video_state and (int(video_state.group(2), 16) & 2):
                video_external_active = video_state.group(1) == b'42'
            audio_state = re.match(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 [0-9A-F]{2} D4 (42|43) ([0-9A-F]{2}) [0-9A-F]{2}$', clean)
            if audio_state and (int(audio_state.group(2), 16) & 1):
                audio_external_active = audio_state.group(1) == b'42'
                audio_event = audio_power.update(audio_external_active, video_external_active,
                                                 overlay_active(), time.monotonic())
                if audio_event:
                    send_livi_key(audio_event)
            key = phone_button.feed(clean)
            source_pressed = source_button.feed(clean)
            media_pressed = media_button.feed(clean)
            track_events = track_buttons.feed(clean)
            now = time.monotonic()
            if args.livi_restart_service and restart_button.feed(clean):
                if last_livi_restart is None or now - last_livi_restart >= 15.0:
                    try:
                        subprocess.Popen(['systemctl', '--no-block', 'restart', args.livi_restart_service],
                                         start_new_session=True)
                        last_livi_restart = now
                        print('LIVI_RESTART_REQUESTED button', flush=True)
                    except OSError as exc:
                        print('LIVI_RESTART_FAILED %s' % exc, flush=True)
                else:
                    print('LIVI_RESTART_SKIPPED cooldown', flush=True)
            if audio_external_active and not overlay_active():
                for track_event in track_events:
                    send_livi_key(track_event)
            if clean.startswith(b'TIRTA_RX D 120 -> 122 C=F N=10 DATA=00 25 B2 85 '):
                print('BUTTON_FRAME ' + clean.decode('ascii', 'replace'), flush=True)
            elif re.match(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 12 B2 43 ', clean):
                print('DISPLAY_RELEASE ' + clean.decode('ascii', 'replace'), flush=True)
            if re.match(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 12 B2 42 ', clean):
                display_retry_at = None
            if key == 'phone':
                if overlay_active(): close_overlay()
                send_livi_key('answer')
            elif key == 'map':
                if overlay_active(): close_overlay()
            elif source_pressed or media_pressed:
                if not overlay_active() or overlay_kind != 'source':
                    open_overlay()
                else:
                    # A live ffplay process does not prove the head switched to RGB.
                    request_overlay_display()
            # MEDIA or another head-selected mode releases the external view.
            if re.match(rb'^TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 12 B2 43 ', clean):
                if overlay_active(): close_overlay()
            m = pattern.search(line.rstrip(b'\r'))
            if not m:
                if line.startswith((b'STOPPED ', b'ACTIVE_STARTED ', b'TIRTA_FUNCTIONS=',
                                    b'PROFILE_', b'TIRTA_TX_ATTEMPT B 122 -> 1FF',
                                    b'TIRTA_TX_ATTEMPT D 122 -> 120', b'TX_RESULT ',
                                    b'CY12_HEAD_03', b'CY12_AUDIO_', b'CY12_SOURCE_KEY_', b'CY12_DISPLAY_')):
                    print('NANO ' + line.rstrip(b'\r').decode('ascii', 'replace'), flush=True)
                if (args.trace_control and line.startswith(b'TIRTA_RX D ')) or (
                    line.startswith(b'TIRTA_RX D ') and b' D4 ' in line
                ):
                    print('AVC ' + line.rstrip(b'\r').decode('ascii', 'replace'), flush=True)
                continue
            x, y, x2, y2 = (int(v, 16) for v in m.groups())
            if overlay_active():
                if (x, y, x2, y2) == (0, 0, 0, 0):
                    # A back press is valid only if it started within the button.
                    action = overlay_touch
                    overlay_touch = None
                    source_highlight(None)
                    if overlay_kind == 'source' and action in ('fm', 'am', 'cd', 'aux', 'dab', 'xm', 'vtr', 'external'):
                        close_overlay()
                        audio_power.suppress_source_change(time.monotonic())
                        os.write(serial, {'fm': b'FM\n', 'am': b'AM\n', 'cd': b'CD\n',
                                          'aux': b'AUX\n', 'dab': b'DAB\n', 'xm': b'XM\n',
                                          'vtr': b'VTR\n', 'external': b'AUD1\n'}[action])
                        print('SOURCE_SELECTED ' + action, flush=True)
                    elif action == 'back':
                        close_overlay()
                elif (x, y) == (x2, y2) and overlay_touch is None:
                    overlay_touch = source_menu_target(x, y) or 'other'
                    source_highlight(overlay_touch)
                continue
            if (x, y, x2, y2) == (0, 0, 0, 0):
                if pressed:
                    emit(EV_KEY, BTN_TOUCH, 0); report()
                    print('RELEASE', flush=True)
                pressed = False; last = None
                continue
            if (x, y) != (x2, y2):
                print('MISMATCH %02X %02X %02X %02X' % (x, y, x2, y2), flush=True)
                continue
            if last != (x, y) or not pressed:
                emit(EV_ABS, ABS_X, x * 257)
                emit(EV_ABS, ABS_Y, (255 - y) * 257)
                if not pressed:
                    emit(EV_KEY, BTN_TOUCH, 1)
                report()
                print('TOUCH x=%d y=%d' % (x, y), flush=True)
            pressed = True; last = (x, y)
        if len(buf) > 8192:
            buf.clear()
finally:
    if livi_keys is not None and livi_keys.poll() is None:
        if livi_keys.stdin: livi_keys.stdin.close()
        try:
            livi_keys.wait(timeout=1)
        except subprocess.TimeoutExpired:
            livi_keys.terminate()
            livi_keys.wait()
    if overlay_active(): close_overlay()
    if ui is not None:
        if pressed:
            emit(EV_KEY, BTN_TOUCH, 0); report()
        try:
            fcntl.ioctl(ui, UI_DEV_DESTROY)
        finally:
            os.close(ui)
    if serial is not None:
        os.close(serial)
