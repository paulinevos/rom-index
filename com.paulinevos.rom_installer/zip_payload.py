"""Checks that a downloaded ZIP is one retro-go can actually open.

retro-go's README is explicit: "ZIP archives should contain only one ROM file
and nothing else." itch.io uploads routinely bundle a readme, a manual or
screenshots alongside the ROM, and such an archive fails at boot rather than at
install. MicroPythonOS makes this worse by reading only the *first* local
header when it computes a CRC, so a multi-file archive also gets the wrong
CRC32 and the wrong box art.

Rejecting here turns a mystifying "the game won't start" into a clear message
while the file is still a .part.
"""

import struct

_EOCD_SIGNATURE = b"PK\x05\x06"
_EOCD_STRUCT = "<IHHHHIIH"
_EOCD_SIZE = 22
_CENTRAL_HEADER_STRUCT = "<IHHHHHHIIIHHHHHII"
_CENTRAL_HEADER_SIZE = 46
_CENTRAL_HEADER_MAGIC = 0x02014B50
_TOTAL_ENTRIES = 4
_CENTRAL_OFFSET = 6
_FILENAME_LENGTH = 10

# A trailing comment is almost always empty; this covers a generous one
# without pulling a large archive tail into a badge's RAM.
_TAIL_BYTES = 4096


class NotAUsableArchive(Exception):
    pass


class ZipPayload:
    """The single file a retro-go-compatible archive is allowed to hold."""

    def __init__(self, name):
        self.name = name

    @classmethod
    def read_from(cls, path):
        handle = open(path, "rb")
        try:
            return cls(cls._sole_entry_name(handle))
        finally:
            handle.close()

    def must_be_playable_on(self, platform):
        # The archive holds the real ROM, so its extension is what retro-go
        # dispatches on, not the .zip we downloaded.
        if platform.accepts(self.name):
            return
        raise NotAUsableArchive(
            "archive holds {}, which {} cannot run".format(self.name, platform.display_name))

    @classmethod
    def _sole_entry_name(cls, handle):
        directory_offset, entries = cls._read_end_record(handle)
        if entries != 1:
            raise NotAUsableArchive(
                "archive holds {} files; retro-go needs exactly one ROM and nothing else".format(
                    entries))
        return cls._read_first_name(handle, directory_offset)

    @staticmethod
    def _read_end_record(handle):
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - _TAIL_BYTES))
        tail = handle.read()
        position = tail.rfind(_EOCD_SIGNATURE)
        if position < 0 or len(tail) - position < _EOCD_SIZE:
            raise NotAUsableArchive("not a ZIP archive, or it is truncated")
        fields = struct.unpack(_EOCD_STRUCT, tail[position:position + _EOCD_SIZE])
        return fields[_CENTRAL_OFFSET], fields[_TOTAL_ENTRIES]

    @staticmethod
    def _read_first_name(handle, directory_offset):
        handle.seek(directory_offset)
        header = handle.read(_CENTRAL_HEADER_SIZE)
        if len(header) < _CENTRAL_HEADER_SIZE:
            raise NotAUsableArchive("archive directory is truncated")
        fields = struct.unpack(_CENTRAL_HEADER_STRUCT, header)
        if fields[0] != _CENTRAL_HEADER_MAGIC:
            raise NotAUsableArchive("archive directory is corrupt")
        return handle.read(fields[_FILENAME_LENGTH]).decode()
