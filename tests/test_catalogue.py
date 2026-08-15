"""Runs the hardware-independent logic under desktop CPython.

`mpos` only exists on the device, so it is stubbed here. Anything importing
lvgl (the activity itself) is out of scope for this file.
"""

import json
import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: F401  installs the mpos stub and app import path

from catalogue import Catalogue, CatalogueEntry, CatalogueError  # noqa: E402
from catalogue_filter import DEFAULT_PLATFORMS, CatalogueFilter  # noqa: E402
from rom_platform import RomPlatform, UnknownPlatform  # noqa: E402


def index_with(*records):
    return json.dumps({"schema": 1, "catalog": list(records)})


def a_record(**overrides):
    record = {
        "title": "Micro Mages",
        "author": "Morphcat",
        "licence": "freeware",
        "platform": "nes",
        "url": "https://example.test/micromages.nes",
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

    def test_refuses_a_url_the_badge_cannot_fetch_without_a_session(self):
        for url in ("http://example.test/a.nes", "", None):
            with self.assertRaises(CatalogueError):
                CatalogueEntry(a_record(url=url))

    def test_keeps_the_source_page_for_attribution(self):
        entry = CatalogueEntry(a_record(source_page="https://x.itch.io/micromages"))
        self.assertEqual(entry.source_page, "https://x.itch.io/micromages")

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

    def test_default_keeps_every_console_the_launcher_browses(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="NES"),
            a_record(title="GB", platform="gb", filename="a.gb"),
            a_record(title="Lynx", platform="lnx", filename="a.lnx"),
            a_record(title="Game and Watch", platform="gw", filename="a.gw"),
        ))
        kept = catalogue.matching(CatalogueFilter())
        self.assertEqual([entry.title for entry in kept],
                         ["Game and Watch", "GB", "Lynx", "NES"])

    def test_narrows_to_the_configured_consoles(self):
        catalogue = Catalogue.parse(index_with(
            a_record(title="NES"),
            a_record(title="Lynx", platform="lnx", filename="a.lnx"),
        ))
        kept = catalogue.matching(CatalogueFilter(("nes",)))
        self.assertEqual([entry.title for entry in kept], ["NES"])

    def test_the_default_platform_list_tracks_rom_platform(self):
        self.assertEqual(set(DEFAULT_PLATFORMS), set(RomPlatform.all_subdirectories()))

    def test_names_only_the_consoles_it_actually_narrows_to(self):
        self.assertEqual(CatalogueFilter().describe_roms(), "ROMs")
        self.assertEqual(CatalogueFilter(("nes", "gb")).describe_roms(), "NES/GB ROMs")


class GameAndWatchTest(unittest.TestCase):

    def test_takes_no_zip_because_retro_go_registers_gw_without_it(self):
        self.assertFalse(RomPlatform("gw").accepts("game.zip"))
        self.assertTrue(RomPlatform("gw").accepts("game.gw"))


class ShippedIndexTest(unittest.TestCase):

    def test_every_shipped_entry_parses_and_survives_the_default_filter(self):
        index = Path(__file__).resolve().parent.parent / "index" / "index.json"
        published = Catalogue.parse(index.read_text())
        # A record the app silently skips would be invisible on the badge, so
        # assert the whole file survives rather than merely that it parses.
        self.assertEqual(len(published), len(json.loads(index.read_text())["catalog"]))
        self.assertFalse(published.matching(CatalogueFilter()).is_empty())

    def test_every_shipped_rom_is_present_with_the_stated_hash(self):
        import hashlib

        root = Path(__file__).resolve().parent.parent
        for record in json.loads((root / "index" / "index.json").read_text())["catalog"]:
            rom = root / "roms" / record["filename"]
            self.assertTrue(rom.exists(), "{} is indexed but not in roms/".format(rom.name))
            digest = hashlib.sha256(rom.read_bytes()).hexdigest()
            self.assertEqual(digest, record["sha256"], record["filename"])
            self.assertEqual(rom.stat().st_size, record["size"], record["filename"])


if __name__ == "__main__":
    unittest.main()
