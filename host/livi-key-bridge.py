#!/usr/bin/env python3
"""Forward fresh key presses to LIVI's local core IPC as the livi user."""
import json
import os
import select
import socket
import struct
import time

runtime_dir = os.environ.get('XDG_RUNTIME_DIR', '/run/user/%d' % os.getuid())
SOCKET = os.environ.get('GT86_LIVI_SOCKET', os.path.join(runtime_dir, 'livi', 'core.sock'))
MAX_FRAME = 16 * 1024 * 1024


def frame(message):
    data = json.dumps(message, separators=(',', ':')).encode('utf-8')
    return struct.pack('<I', len(data)) + data


def recv_exact(sock, size):
    result = bytearray()
    while len(result) < size:
        part = sock.recv(size - len(result))
        if not part:
            raise EOFError('LIVI disconnected')
        result.extend(part)
    return bytes(result)


def find_bindings(value):
    if isinstance(value, dict):
        if all(isinstance(value.get(k), str) and value[k] for k in ('next', 'prev', 'acceptPhone')):
            return {'next': value['next'], 'previous': value['prev'], 'answer': value['acceptPhone']}
        for child in value.values():
            result = find_bindings(child)
            if result:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_bindings(child)
            if result:
                return result
    return None


def connect():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(SOCKET)
        sock.sendall(frame({'type': 'hello', 'protocol': 11, 'client': 'gt86-buttons'}))
        length, = struct.unpack('<I', recv_exact(sock, 4))
        if length > MAX_FRAME:
            raise ValueError('oversized welcome')
        reply = json.loads(recv_exact(sock, length))
        if reply.get('type') != 'welcome' or reply.get('protocol') != 11:
            raise ValueError('LIVI handshake refused')
        bindings = find_bindings(reply.get('state', {}).get('config', {}))
        if not bindings:
            raise ValueError('LIVI key bindings unavailable')
        print('LIVI_KEYS_READY', flush=True)
        return sock, bindings
    except Exception:
        sock.close()
        raise


def run():
    sock = None
    bindings = None
    buf = bytearray()
    action_id = 1
    while True:
        if sock is None:
            try:
                sock, bindings = connect()
            except (OSError, EOFError, ValueError) as exc:
                print('LIVI_KEYS_WAIT ' + str(exc), flush=True)
                time.sleep(1)
                continue
        try:
            readable, _, _ = select.select([0, sock], [], [], 1)
            if sock in readable and not sock.recv(65536):
                raise EOFError('LIVI disconnected')
            if 0 not in readable:
                continue
            data = os.read(0, 4096)
            if not data:
                return
            buf.extend(data)
            while b'\n' in buf:
                line, _, remaining = buf.partition(b'\n')
                buf = bytearray(remaining)
                try:
                    name, stamp = line.decode('ascii').split(' ', 1)
                    age = time.monotonic() - float(stamp)
                    if not 0 <= age < 1.5:
                        continue
                    if name in ('audio_play', 'audio_pause'):
                        control = 'play' if name == 'audio_play' else 'pause'
                        sock.sendall(frame({'type': 'action', 'id': action_id,
                                            'action': {'kind': 'media', 'control': control}}))
                        action_id = 1 if action_id >= 0xFFFFFFFF else action_id + 1
                    else:
                        code = bindings.get(name)
                        if not code:
                            continue
                        for down in (True, False):
                            sock.sendall(frame({'type': 'input', 'input': {'kind': 'key', 'code': code, 'down': down}}))
                    print('LIVI_KEY_SENT ' + name, flush=True)
                except (ValueError, UnicodeError):
                    continue
            if len(buf) > 8192:
                buf.clear()
        except (OSError, EOFError) as exc:
            print('LIVI_KEYS_DISCONNECTED ' + str(exc), flush=True)
            sock.close()
            sock = None


if __name__ == '__main__':
    run()
