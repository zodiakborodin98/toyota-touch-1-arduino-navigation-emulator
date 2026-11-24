from avc_media_keys import TrackButtons, AudioPowerEvents, LiviRestartButton

keys = TrackButtons()
prefix = b'TIRTA_RX D 120 -> 122 C=F N=06 DATA=00 25 D4 84 '
assert keys.feed(prefix + b'80 00') == ('next',)
assert keys.feed(prefix + b'80 00') == ()
assert keys.feed(prefix + b'00 00') == ()
assert keys.feed(prefix + b'40 00') == ('previous',)
assert keys.feed(prefix + b'40 00') == ()
assert keys.feed(prefix + b'00 81') == ()
assert keys.feed(prefix + b'01 00') == ()
assert keys.feed(prefix + b'C0 00') == ('next', 'previous')
assert keys.feed(b'unrelated') == ()
power = AudioPowerEvents()
assert power.update(True, True, False, 1.0) is None
assert power.update(True, True, False, 1.1) is None
assert power.update(False, True, False, 2.0) == 'audio_pause'
assert power.update(True, True, False, 3.0) == 'audio_play'
power.suppress_source_change(4.0)
assert power.update(False, True, False, 4.1) is None
assert power.update(True, True, False, 7.1) == 'audio_play'
assert power.update(False, False, False, 8.0) is None
assert power.update(True, True, True, 9.0) is None
restart = LiviRestartButton()
assert restart.feed(prefix + b'01 00')
assert not restart.feed(prefix + b'01 00')  # repeated state, not another press
assert not restart.feed(b'unrelated')
assert not restart.feed(prefix + b'00 00')
assert not restart.feed(prefix + b'00 00')
assert restart.feed(prefix + b'81 00')  # another key can be down
assert not restart.feed(prefix + b'80 00')
assert not restart.feed(prefix + b'40 00')  # track buttons alone do not restart
print('track button edges and rotary-noise checks passed')
