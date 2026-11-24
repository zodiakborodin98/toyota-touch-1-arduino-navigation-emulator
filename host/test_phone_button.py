import unittest
from phone_button import PhoneButton

def frame(first=0, last=0):
    values = [first] + [0] * 10 + [last]
    return ('TIRTA_RX D 120 -> 122 C=F N=10 DATA=00 25 B2 85 ' +
            ' '.join('%02X' % x for x in values)).encode()

class PhoneButtonTest(unittest.TestCase):
    def test_edges_and_release(self):
        d = PhoneButton()
        self.assertEqual(d.feed(frame(4)), 'phone')
        self.assertIsNone(d.feed(frame(4)))
        self.assertIsNone(d.feed(frame()))
        self.assertEqual(d.feed(frame(4)), 'phone')
        self.assertIsNone(d.feed(frame()))
        self.assertEqual(d.feed(frame(2)), 'map')

    def test_other_events_and_bad_frames(self):
        d = PhoneButton()
        self.assertIsNone(d.feed(frame(last=0x10)))
        self.assertIsNone(d.feed(frame(last=0x80)))
        self.assertIsNone(d.feed(frame(4).replace(b'120 -> 122', b'130 -> 122')))
        self.assertIsNone(d.feed(frame(4)[:-3]))
        self.assertEqual(d.feed(frame(4)), 'phone')

if __name__ == '__main__':
    unittest.main()
