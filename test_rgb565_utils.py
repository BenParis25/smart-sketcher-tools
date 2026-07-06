import unittest

from rgb565_utils import rgb_to_rgb565_bytes


class Rgb565PackingTests(unittest.TestCase):
    def test_black(self):
        self.assertEqual(rgb_to_rgb565_bytes(0, 0, 0), (0x00, 0x00))

    def test_red(self):
        self.assertEqual(rgb_to_rgb565_bytes(255, 0, 0), (0x00, 0xF8))

    def test_green(self):
        self.assertEqual(rgb_to_rgb565_bytes(0, 255, 0), (0xE0, 0x07))

    def test_blue(self):
        self.assertEqual(rgb_to_rgb565_bytes(0, 0, 255), (0x1F, 0x00))

    def test_white(self):
        self.assertEqual(rgb_to_rgb565_bytes(255, 255, 255), (0xFF, 0xFF))


if __name__ == "__main__":
    unittest.main()