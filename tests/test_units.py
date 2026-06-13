import unittest

from devtidy.units import human_size, parse_duration, parse_size


class UnitParsingTests(unittest.TestCase):
    def test_parse_sizes(self):
        self.assertEqual(parse_size("100MB"), 100_000_000)
        self.assertEqual(parse_size("2 MiB"), 2 * 1024 * 1024)
        self.assertEqual(parse_size("1TB"), 1000**4)
        self.assertEqual(parse_size("512"), 512)

    def test_parse_duration(self):
        self.assertEqual(parse_duration("24h"), 86_400)
        self.assertEqual(parse_duration("2w"), 1_209_600)

    def test_human_size(self):
        self.assertEqual(human_size(1024), "1.0 KiB")


if __name__ == "__main__":
    unittest.main()
