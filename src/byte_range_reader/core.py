import os


class RangeError(ValueError):
    """Raised when a caller requests a byte range that cannot be served.

    Subclasses ValueError so existing code that catches ValueError for bad
    input keeps working, while callers that care specifically about range
    problems can catch this narrower type.
    """


class ByteRangeReader:
    """Read fixed byte ranges from a large file without loading it all.

    Each call opens the file, seeks to ``start``, and reads ``length`` bytes.
    We deliberately do NOT keep the file open between calls: long-lived file
    handles are a real source of resource leaks in services that read many
    different files, and the seek cost is negligible compared to the syscall
    we have to make anyway. If a caller needs tight loops over adjacent
    ranges, they should batch those ranges themselves rather than relying on
    this class to hold state.
    """

    def __init__(self, path):
        if not isinstance(path, (str, bytes, os.PathLike)):
            raise TypeError("path must be str, bytes, or os.PathLike")
        self.path = os.fspath(path)
        # Resolve and stat once at construction so we can fail fast for a
        # missing file, and so size is consistent across reads (a file could
        # in principle be replaced between calls; we treat the size seen at
        # construction as the contract).
        if not os.path.isfile(self.path):
            raise FileNotFoundError("not a regular file: {!r}".format(self.path))
        self._size = os.path.getsize(self.path)

    @property
    def size(self):
        return self._size

    def read(self, start, length):
        """Return exactly ``length`` bytes starting at ``start``.

        Raises RangeError if ``start`` is negative, if ``length`` is not a
        non-negative int, or if ``[start, start+length)`` runs past EOF.

        We require the full range to fit inside the file. Returning a short
        read silently would hide caller bugs (off-by-one on the end offset is
        the classic one) and force every caller to re-check the returned
        length. A hard error makes the contract explicit.
        """
        if not isinstance(start, int) or isinstance(start, bool):
            raise TypeError("start must be an int")
        if not isinstance(length, int) or isinstance(length, bool):
            raise TypeError("length must be an int")
        if start < 0:
            raise RangeError("start must be non-negative")
        if length < 0:
            raise RangeError("length must be non-negative")
        if start > self._size:
            # start == size is allowed only when length == 0; handled by the
            # next check so we can give a precise message.
            raise RangeError(
                "start {} is past end of file (size {})".format(start, self._size)
            )
        if start + length > self._size:
            raise RangeError(
                "range [{}, {}) extends past end of file (size {})".format(
                    start, start + length, self._size
                )
            )
        if length == 0:
            return b""
        with open(self.path, "rb") as f:
            f.seek(start)
            data = f.read(length)
        # Defensive: read() can return fewer bytes than requested in rare
        # low-level cases (interrupted read on some platforms). Since we
        # already validated the range against the stat'd size, a short read
        # here indicates something genuinely wrong and should not be hidden.
        if len(data) != length:
            raise RangeError(
                "expected {} bytes at offset {}, got {}".format(
                    length, start, len(data)
                )
            )
        return data
