import unittest

from cpushowspeed.parallel import pmap


def square(x):
    return x * x


class ParallelTests(unittest.TestCase):
    def test_parallel_and_serial_maps_agree_in_order(self):
        items = list(range(50))
        expected = [x * x for x in items]
        self.assertEqual(pmap(square, items, jobs=1), expected)
        self.assertEqual(pmap(square, items, jobs=4, chunksize=3), expected)

    def test_empty_input(self):
        self.assertEqual(pmap(square, [], jobs=4), [])


if __name__ == "__main__":
    unittest.main()
