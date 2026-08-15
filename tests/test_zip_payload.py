"""Verifies the retro-go single-file archive rule against real ZIPs."""

import tempfile
import unittest
import zipfile

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: F401  installs the mpos stub and app import path

from rom_platform import RomPlatform  # noqa: E402
from zip_payload import NotAUsableArchive, ZipPayload  # noqa: E402


def a_zip_containing(*names):
    handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(handle, "w") as archive:
        for name in names:
            archive.writestr(name, b"\x00" * 64)
    handle.close()
    return handle.name


class ZipPayloadTest(unittest.TestCase):

    def test_reads_the_name_of_a_single_entry_archive(self):
        self.assertEqual(
            ZipPayload.read_from(a_zip_containing("micromages.nes")).name,
            "micromages.nes")

    def test_rejects_the_readme_itch_io_ships_beside_the_rom(self):
        path = a_zip_containing("micromages.nes", "README.txt")
        with self.assertRaises(NotAUsableArchive) as caught:
            ZipPayload.read_from(path)
        self.assertIn("exactly one ROM", str(caught.exception))

    def test_rejects_an_empty_archive(self):
        with self.assertRaises(NotAUsableArchive):
            ZipPayload.read_from(a_zip_containing())

    def test_rejects_a_file_that_is_not_a_zip(self):
        handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        handle.write(b"not a zip at all")
        handle.close()
        with self.assertRaises(NotAUsableArchive):
            ZipPayload.read_from(handle.name)

    def test_checks_the_inner_extension_not_the_zip(self):
        payload = ZipPayload("game.gb")
        payload.must_be_playable_on(RomPlatform("gb"))
        with self.assertRaises(NotAUsableArchive):
            payload.must_be_playable_on(RomPlatform("nes"))


if __name__ == "__main__":
    unittest.main()
