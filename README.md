# Byte Range Reader

Reads arbitrary byte ranges from large files without loading the entire file into memory.

```python
from byte_range_reader import ByteRangeReader

reader = ByteRangeReader(__file__)
chunk = reader.read(1, 4)  # bytes [1, 5)
```

## Why this exists

For files that are too large to read into memory (multi-gigabyte logs, packed
archives, binary datasets), the common need is to pull a specific slice by
offset and length. `ByteRangeReader` validates the range against the file's
size and returns exactly the requested bytes via a seek plus read, keeping no
file handle open between calls.

The trade-off: each `read` call opens and closes the file. That is a couple of
extra syscalls per read, which is fine for occasional access across many
different files but would be wasteful for tight loops over adjacent ranges of
one file. If you need that, batch the ranges yourself.

## The awkward edge

`read` requires the requested range to fit entirely within the file. A range
that runs past EOF raises `RangeError` (a subclass of `ValueError`) rather than
returning a short read. This is deliberate: silent short reads hide off-by-one
bugs in the caller and force every consumer to re-check the returned length.
If you want "read up to N bytes," compute the clamped length yourself before
calling.

`start == size` is permitted only when `length == 0`; any positive length at
that offset is past EOF and raises.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

