#!/usr/bin/env python3
"""Adds a ROM to roms/ and writes its catalogue entry.

The mechanical fields — filename, size, sha256 and the raw URL — are derived
from the file itself, which is where hand-written entries go wrong. Everything
requiring judgement is asked for on the command line.

    python3 index/add_rom.py ~/Downloads/katkrat.gb \\
        --title Katkrat --author SevenLuchtveer \\
        --platform gbc --licence author-permitted \\
        --source-page https://sevenluchtveer.itch.io/katkrat
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from validate import EXTENSIONS, problems_with

REPOSITORY = Path(__file__).resolve().parent.parent
ROM_DIRECTORY = REPOSITORY / "roms"
INDEX = REPOSITORY / "index" / "index.json"
DEFAULT_BRANCH = "main"


class RomFile:
    """A ROM on disk, and everything about it the catalogue can derive."""

    def __init__(self, path):
        self.path = path
        self.filename = path.name
        self.size = path.stat().st_size
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def published_as(cls, source, platform):
        cls._refuse_wrong_extension(source.name, platform)
        return cls(cls._copy_into_repository(source))

    def raw_url(self, url_base):
        return "{}/{}".format(url_base.rstrip("/"), self.filename)

    @staticmethod
    def _copy_into_repository(source):
        destination = ROM_DIRECTORY / source.name
        if destination.exists() and destination.read_bytes() == source.read_bytes():
            return destination
        if destination.exists():
            raise SystemExit(
                "roms/{} already exists with different contents".format(source.name))
        ROM_DIRECTORY.mkdir(exist_ok=True)
        shutil.copy2(source, destination)
        print("copied {} -> roms/{}".format(source, source.name))
        return destination

    @staticmethod
    def _refuse_wrong_extension(filename, platform):
        accepted = EXTENSIONS.get(platform)
        if not accepted:
            raise SystemExit("unknown platform '{}'; one of: {}".format(
                platform, " ".join(sorted(EXTENSIONS))))
        if not filename.lower().endswith(accepted):
            raise SystemExit("{} cannot run '{}'; it accepts {}".format(
                platform, filename, " ".join(accepted)))


class Catalogue:
    """The index file, which stays sorted by title so diffs stay readable."""

    def __init__(self, path):
        self._path = path
        self._document = json.loads(path.read_text())

    def refuse_duplicate(self, filename):
        for entry in self._document["catalog"]:
            if entry.get("filename") == filename:
                raise SystemExit(
                    "{} is already in the index; remove it first to replace it".format(
                        filename))

    def add(self, entry):
        self._document["catalog"].append(entry)
        self._document["catalog"].sort(key=lambda record: record["title"].lower())
        self._path.write_text(json.dumps(self._document, indent=2) + "\n")


def raw_url_base(branch):
    slug = repository_slug()
    return "https://raw.githubusercontent.com/{}/{}/roms".format(slug, branch)


def repository_slug():
    remote = subprocess.run(
        ["git", "-C", str(REPOSITORY), "remote", "get-url", "origin"],
        capture_output=True, text=True)
    if remote.returncode != 0:
        raise SystemExit("no git remote 'origin'; pass --url-base explicitly")
    url = remote.stdout.strip().removesuffix(".git")
    if url.startswith("git@"):
        return url.split(":", 1)[1]
    return "/".join(url.split("/")[-2:])


def entry_for(rom, arguments, url_base):
    entry = {
        "title": arguments.title,
        "author": arguments.author,
        "licence": arguments.licence,
        "platform": arguments.platform,
        "url": rom.raw_url(url_base),
        "filename": rom.filename,
        "size": rom.size,
        "sha256": rom.sha256,
        "free": arguments.price == 0,
    }
    if arguments.price:
        entry["price"] = arguments.price
    for name, value in (("source_page", arguments.source_page),
                        ("art_url", arguments.art_url)):
        if value:
            entry[name] = value
    return entry


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rom", type=Path, help="the ROM file to publish")
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--platform", required=True,
                        help="one of: " + " ".join(sorted(EXTENSIONS)))
    parser.add_argument("--licence", required=True,
                        help="must permit redistribution, e.g. author-permitted")
    parser.add_argument("--source-page", default="",
                        help="where the ROM was published; attribution only")
    parser.add_argument("--art-url", default="")
    parser.add_argument("--price", type=int, default=0,
                        help="in cents; omit for free")
    parser.add_argument("--branch", default=DEFAULT_BRANCH,
                        help="branch the raw URL points at (default: %(default)s)")
    parser.add_argument("--url-base",
                        help="override the derived raw URL prefix")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    if not arguments.rom.is_file():
        raise SystemExit("no such file: {}".format(arguments.rom))

    rom = RomFile.published_as(arguments.rom, arguments.platform)
    catalogue = Catalogue(INDEX)
    catalogue.refuse_duplicate(rom.filename)

    url_base = arguments.url_base or raw_url_base(arguments.branch)
    entry = entry_for(rom, arguments, url_base)

    problems = list(problems_with(entry, 0))
    if problems:
        print("\n".join(problems))
        raise SystemExit("entry is not valid; nothing was written to the index")

    catalogue.add(entry)
    print(json.dumps(entry, indent=2))
    print("\nadded to index/index.json - commit roms/{} with it".format(rom.filename))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
