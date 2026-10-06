import os
import tempfile
import unittest

from byte_range_reader import ByteRangeReader, RangeError


class TestByteRangeReader(unittest.TestCase):
    def setUp(self):
        self._fd, self.path = tempfile.mkstemp(prefix="brr_", suffix=".bin")
        os.close(self._fd)
        self.data = bytes(range(256)) * 4  # 1024 bytes
        with open(self.path, "wb") as f:
            f.write(self.data)

    def tearDown(self):
        os.unlink(self.path)

    def test_reads_exact_range(self):
        r = ByteRangeReader(self.path)
        chunk = r.read(100, 10)
        self.assertEqual(chunk, self.data[100:110])

    def test_reads_from_offset_zero(self):
        r = ByteRangeReader(self.path)
        self.assertEqual(r.read(0, 4), self.data[:4])

    def test_read_at_last_byte(self):
        r = ByteRangeReader(self.path)
        self.assertEqual(r.read(r.size - 1, 1), self.data[-1:])

    def test_size_matches_file(self):
        r = ByteRangeReader(self.path)
        self.assertEqual(r.size, len(self.data))

    def test_zero_length_returns_empty_bytes(self):
        r = ByteRangeReader(self.path)
        self.assertEqual(r.read(0, 0), b"")

    def test_zero_length_at_eof_is_allowed(self):
        r = ByteRangeReader(self.path)
        self.assertEqual(r.read(r.size, 0), b"")

    def test_negative_start_raises_range_error(self):
        r = ByteRangeReader(self.path)
        with self.assertRaises(RangeError):
            r.read(-1, 4)

    def test_negative_length_raises_range_error(self):
        r = ByteRangeReader(self.path)
        with self.assertRaises(RangeError):
            r.read(0, -1)

    def test_range_past_eof_raises_range_error(self):
        r = ByteRangeReader(self.path)
        with self.assertRaises(RangeError):
            r.read(r.size - 4, 10)

    def test_start_past_eof_raises_range_error(self):
        r = ByteRangeReader(self.path)
        with self.assertRaises(RangeError):
            r.read(r.size + 1, 1)

    def test_missing_file_raises_at_construction(self):
        missing = self.path + ".does_not_exist"
        with self.assertRaises(FileNotFoundError):
            ByteRangeReader(missing)

    def test_rejects_non_int_arguments(self):
        r = ByteRangeReader(self.path)
        with self.assertRaises(TypeError):
            r.read("0", 4)
        with self.assertRaises(TypeError):
            r.read(0, 3.5)

    def test_bool_is_not_accepted_as_int(self):
        # bool is a subclass of int in Python; accepting True as 1 would be a
        # silent footgun. We reject it explicitly.
        r = ByteRangeReader(self.path)
        with self.assertRaises(TypeError):
            r.read(True, 4)
        with self.assertRaises(TypeError):
            r.read(0, False)


if __name__ == "__main__":
    unittest.main()
