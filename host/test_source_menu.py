from source_menu import SourceButton, MediaButton, source_menu_target
button = SourceButton()
prefix = b'TIRTA_RX D 120 -> 122 C=F N=10 DATA=00 25 B2 85 '
pressed = prefix + b'00 00 00 00 00 00 00 00 00 00 00 80'
released = prefix + b'00 00 00 00 00 00 00 00 00 00 00 00'
assert button.feed(pressed)
assert not button.feed(pressed)
assert not button.feed(released)
assert button.feed(pressed)
assert not button.feed(b'unrelated line')
media = MediaButton()
media_down = prefix + b'01 00 00 00 00 00 00 00 00 00 00 00'
assert media.feed(media_down)
assert not media.feed(media_down)
assert not media.feed(released)
assert media.feed(media_down)
assert not media.feed(pressed)
for x, y, target in ((40,180,'fm'),(125,180,'am'),(210,180,'cd'),
                     (40,120,'aux'),(125,120,'external'),(220,230,'back')):
    assert source_menu_target(x,y) == target
assert source_menu_target(210, 60) is None
assert source_menu_target(210, 120) is None
assert source_menu_target(40, 60) is None
print('source menu button and touch checks passed')
