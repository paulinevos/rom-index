"""Runs the hardware-independent logic under desktop CPython.

`mpos` only exists on the device, so it is stubbed here. Anything importing
lvgl (the activity itself) is out of scope for this file.
"""

import json
import sys
import types
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "com.paulinevos.rom_installer"
sys.path.insert(0, str(APP))

_mpos = types.ModuleType("mpos")
_mpos.DownloadManager = None
sys.modules.setdefault("mpos", _mpos)

from catalogue import Catalogue, CatalogueEntry, CatalogueError  # noqa: E402
from catalogue_filter import CatalogueFilter  # noqa: E402
from rom_platform import RomPlatform, UnknownPlatform  # noqa: E402


def index_with(*records):
    return json.dumps({"schema": 1, "catalog": list(records)})


def a_record(**overrides):
    record = {
        "title": "Micro Mages",
        "author": "Morphcat",
        "licence": "freeware",
        "platform": "nes",
        "itch_game_id": 123,
        "itch_upload_id": 456,
        "filename": "micromages.nes",
        "sha256": "ab" * 32,
        "size": 40976,
    }
    record.update(overrides)
    return record


class RomPlatformTest(unittest.TestCase):

    def test_maps_subdirectory_to_launcher_console(self):
        self.assertEqual(RomPlatform("gbc").display_name, "Gameboy Color")

    def test_rejects_a_directory_the_launcher_never_browses(self):
        with self.assertRaises(UnknownPlatform):
            RomPlatform("n64")

    def test_accepts_the_extensions_the_launcher_lists(self):
        nes = RomPlatform("nes")
        self.assertTrue(nes.accepts("game.NES"))
        self.assertTrue(nes.accepts("game.zip"))
        self.assertFalse(nes.accepts("game.gb"))


class CatalogueEntryTest(unittest.TestCase):

    def test_refuses_a_rom_the_platform_cannot_run(self):
        with self.assertRaises(CatalogueError):
            CatalogueEntry(a_record(platform="gb", filename="game.nes"))

    def test_refuses_a_filename_that_escapes_the_platform_directory(self):
        with self.assertRaises(CatalogueError):
            CatalogueEntry(a_record(filename="../../boot.py"))

    def test_subtitle_names_the_console_and_author(self):
        entry = CatalogueEntry(a_record())
        self.assertEqual(entry.subtitle(), "Nintendo Entertainment System - Morphcat")


class CatalogueTest(unittest.TestCase):

    def test_rejects_an_unsupported_schema(self):
        with self.assertRaises(CatalogueError):
            Catalogue.parse(json.dumps({"schema": 99, "catalog": []}))

    def test_one_bad_record_does_not_hide_the_others(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="Good"),
            a_record(title="Bad", platform="dreamcast"),
            a_record(title="Also missing a filename", filename=None),
        ))
        self.assertEqual([entry.title for entry in catalogue], ["Good"])

    def test_sorts_by_title(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="Zooming"), a_record(title="alpha")))
        self.assertEqual([entry.title for entry in catalogue], ["alpha", "Zooming"])

    def test_filters_by_platform(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="A"),
            a_record(title="B", platform="gb", filename="b.gb"),
        ))
        self.assertEqual(len(catalogue.for_platform("gb")), 1)
        self.assertEqual(catalogue.platform_names(), ["nes", "gb"])


class CatalogueFilterTest(unittest.TestCase):

    def test_default_keeps_only_free_nes_gb_gbc(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="NES free"),
            a_record(title="GB free", platform="gb", filename="a.gb"),
            a_record(title="GBC free", platform="gbc", filename="a.gbc"),
            a_record(title="Lynx", platform="lnx", filename="a.lnx"),
            a_record(title="NES paid", price=500),
        ))
        kept = catalogue.matching(CatalogueFilter())
        self.assertEqual(
            [entry.title for entry in kept], ["GB free", "GBC free", "NES free"])

    def test_an_explicit_free_flag_beats_a_missing_price(self):
        catalogue = Catalogue.parse(index_with(a_record(free=False)))
        self.assertTrue(catalogue.matching(CatalogueFilter()).is_empty())

    def test_free_only_can_be_turned_off(self):
        catalogue = Catalogue.parse(index_with(a_record(price=500)))
        kept = catalogue.matching(CatalogueFilter(("nes",), free_only=False))
        self.assertEqual(len(kept), 1)

    def test_describes_itself_for_the_status_line(self):
        self.assertEqual(CatalogueFilter().describe(), "free NES/GB/GBC")


class GameAndWatchTest(unittest.TestCase):

    def test_takes_no_zip_because_retro_go_registers_gw_without_it(self):
        self.assertFalse(RomPlatform("gw").accepts("game.zip"))
        self.assertTrue(RomPlatform("gw").accepts("game.gw"))


class ShippedIndexTest(unittest.TestCase):

    def test_the_index_in_this_repo_parses(self):
        index = Path(__file__).resolve().parent.parent / "index" / "index.json"
        catalogue = Catalogue.parse(index.read_text())
        self.assertEqual(len(catalogue), 1)


if __name__ == "__main__":
    unittest.main()
