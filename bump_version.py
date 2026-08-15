#!/usr/bin/env python3
"""Raises the app version in MANIFEST.JSON.

The manifest is the only place a version lives — bundle.sh reads it to name
the .mpk — so this edits that one field and leaves the rest of the file byte
for byte alone, keeping release diffs to a single line.

    python3 bump_version.py patch|minor|major
    python3 bump_version.py --set 1.0.0
    python3 bump_version.py --current
"""

import argparse
import re
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "com.paulinevos.rom_installer" / "MANIFEST.JSON"
VERSION_FIELD = re.compile(r'("version"\s*:\s*")(\d+)\.(\d+)\.(\d+)(")')


class Version:

    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, text):
        parts = text.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise SystemExit("'{}' is not a major.minor.patch version".format(text))
        return cls(*(int(part) for part in parts))

    def raised(self, part):
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise SystemExit("cannot bump '{}'".format(part))

    def __str__(self):
        return "{}.{}.{}".format(self.major, self.minor, self.patch)


class Manifest:

    def __init__(self, path):
        self._path = path
        self._text = path.read_text()
        self._match = VERSION_FIELD.search(self._text)
        if not self._match:
            raise SystemExit("no major.minor.patch version field in {}".format(path))

    def current(self):
        return Version(*(int(self._match.group(index)) for index in (2, 3, 4)))

    def write(self, version):
        replacement = r"\g<1>{}\g<5>".format(version)
        self._path.write_text(VERSION_FIELD.sub(replacement, self._text, count=1))


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("part", nargs="?", choices=("major", "minor", "patch"))
    group.add_argument("--set", dest="exact", help="set an exact version")
    group.add_argument("--current", action="store_true",
                       help="print the current version and exit")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    manifest = Manifest(MANIFEST)
    if arguments.current:
        print(manifest.current())
        return 0

    new_version = (Version.parse(arguments.exact) if arguments.exact
                   else manifest.current().raised(arguments.part))
    if str(new_version) == str(manifest.current()):
        raise SystemExit("already at {}".format(new_version))

    manifest.write(new_version)
    print(new_version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
