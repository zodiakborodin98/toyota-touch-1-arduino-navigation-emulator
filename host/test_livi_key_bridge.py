"""Test the real helper against a local fake LIVI socket; no phone required."""
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time

def packet(value):
    data = json.dumps(value, separators=(',', ':')).encode()
    return struct.pack('<I', len(data)) + data

def read_exact(sock, count):
    data = b''
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise AssertionError('socket closed')
        data += part
    return data

def read_packet(sock):
    length, = struct.unpack('<I', read_exact(sock, 4))
    return json.loads(read_exact(sock, length))

with tempfile.TemporaryDirectory(prefix='gt86-livi-test-') as tmp:
    path = os.path.join(tmp, 'core.sock')
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(path)
    server.listen(1)
    server.settimeout(5)
    env = dict(os.environ, GT86_LIVI_SOCKET=path)
    helper = subprocess.Popen([sys.executable, '-u', os.path.join(os.path.dirname(__file__), 'livi-key-bridge.py')],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    try:
        conn, _ = server.accept()
        conn.settimeout(5)
        assert read_packet(conn) == {'type': 'hello', 'protocol': 11, 'client': 'gt86-buttons'}
        conn.sendall(packet({'type': 'welcome', 'protocol': 11, 'state': {'config': {'bindings': {
            'next': 'KeyN', 'prev': 'KeyB', 'acceptPhone': 'KeyA', 'playPause': 'KeyP'}}}}))
        assert helper.stdout.readline().strip() == b'LIVI_KEYS_READY'
        now = time.monotonic()
        for name, stamp in (('next', now - 5), ('next', now), ('previous', now), ('answer', now),
                            ('audio_pause', now), ('audio_play', now)):
            helper.stdin.write(('%s %.6f\n' % (name, stamp)).encode())
        helper.stdin.flush()
        got = [read_packet(conn) for _ in range(8)]
        expected = [{'type': 'input', 'input': {'kind': 'key', 'code': code, 'down': down}}
                    for code in ('KeyN', 'KeyB', 'KeyA') for down in (True, False)]
        expected += [{'type': 'action', 'id': 1, 'action': {'kind': 'media', 'control': 'pause'}},
                     {'type': 'action', 'id': 2, 'action': {'kind': 'media', 'control': 'play'}}]
        assert got == expected, got
        helper.stdin.close()
        assert helper.wait(timeout=5) == 0
        conn.close()
    finally:
        if helper.poll() is None:
            helper.kill()
            helper.wait()
        server.close()
print('LIVI IPC handshake, keys, release and stale input checks passed')
