#!/usr/bin/env python3
"""Writes a catalogue entry for a ROM, deriving everything mechanical.

filename, size, sha256 and the URL are what hand-written entries get wrong,
so they are computed; the command line asks only for judgement.

Committing the ROM to this repo:

    python3 index/add_rom.py ~/Downloads/katkrat.gb \\
        --title Katkrat --author SevenLuchtveer \\
        --platform gbc --licence author-permitted \\
        --source-page https://sevenluchtveer.itch.io/katkrat

Hosting it yourself — the file is fetched so the hash describes what a badge
will actually receive, and a redirecting URL is refused because the badge
cannot follow one:

    python3 index/add_rom.py --url https://example.com/roms/katkrat.gb \\
        --title Katkrat --author SevenLuchtveer \\
        --platform gbc --licence author-permitted
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import urllib.error

from check_urls import fetch
from validate import EXTENSIONS, problems_with

REPOSITORY = Path(__file__).resolve().parent.parent
ROM_DIRECTORY = REPOSITORY / "roms"
INDEX = REPOSITORY / "index" / "index.json"
DEFAULT_BRANCH = "main"


class PublishableRom:
    """A ROM the catalogue can describe, however it was obtained.

    Either it is a file being committed to `roms/`, or it already sits on
    somebody's own server. Both paths end with the same four facts: a
    filename, a size, a hash and the URL a badge will fetch.
    """

    def __init__(self, filename, contents, url):
        self.filename = filename
        self.size = len(contents)
        self.sha256 = hashlib.sha256(contents).hexdigest()
        self.url = url

    @classmethod
    def from_file(cls, source, platform, url_base):
        cls._refuse_wrong_extension(source.name, platform)
        path = cls._copy_into_repository(source)
        return cls(path.name, path.read_bytes(),
                   "{}/{}".format(url_base.rstrip("/"), path.name))

    @classmethod
    def from_url(cls, url, platform, filename=None):
        """Self-hosted: fetch it, so the hash describes what a badge will get."""
        name = filename or url.rstrip("/").rsplit("/", 1)[-1]
        cls._refuse_wrong_extension(name, platform)
        print("fetching {}".format(url))
        try:
            contents = fetch(url)
        except urllib.error.HTTPError as error:
            raise SystemExit("{} -> HTTP {} {}".format(url, error.code, error.reason))
        except (urllib.error.URLError, OSError) as error:
            raise SystemExit("{} -> unreachable ({})".format(url, error))
        print("fetched {} bytes".format(len(contents)))
        return cls(name, contents, url)

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


def entry_for(rom, arguments):
    entry = {
        "title": arguments.title,
        "author": arguments.author,
        "licence": arguments.licence,
        "platform": arguments.platform,
        "url": rom.url,
        "filename": rom.filename,
        "size": rom.size,
        "sha256": rom.sha256,
    }
    for name, value in (("source_page", arguments.source_page),
                        ("art_url", arguments.art_url)):
        if value:
            entry[name] = value
    return entry


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("rom", type=Path, nargs="?",
                        help="a ROM file to commit to roms/")
    source.add_argument("--url",
                        help="an https:// url you already host the ROM at")
    parser.add_argument("--filename",
                        help="name to install as; defaults to the url's last segment")
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--platform", required=True,
                        help="one of: " + " ".join(sorted(EXTENSIONS)))
    parser.add_argument("--licence", required=True,
                        help="must permit redistribution, e.g. author-permitted")
    parser.add_argument("--source-page", default="",
                        help="where the ROM was published; attribution only")
    parser.add_argument("--art-url", default="")
    parser.add_argument("--branch", default=DEFAULT_BRANCH,
                        help="branch the raw URL points at (default: %(default)s)")
    parser.add_argument("--url-base",
                        help="override the derived raw URL prefix")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    rom = obtain(arguments)

    catalogue = Catalogue(INDEX)
    catalogue.refuse_duplicate(rom.filename)
    entry = entry_for(rom, arguments)

    problems = list(problems_with(entry, 0))
    if problems:
        print("\n".join(problems))
        raise SystemExit("entry is not valid; nothing was written to the index")

    catalogue.add(entry)
    print(json.dumps(entry, indent=2))
    print("\nadded to index/index.json{}".format(
        "" if arguments.url else " - commit roms/{} with it".format(rom.filename)))
    return 0


def obtain(arguments):
    if arguments.url:
        return PublishableRom.from_url(
            arguments.url, arguments.platform, arguments.filename)
    if not arguments.rom.is_file():
        raise SystemExit("no such file: {}".format(arguments.rom))
    url_base = arguments.url_base or raw_url_base(arguments.branch)
    return PublishableRom.from_file(arguments.rom, arguments.platform, url_base)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
