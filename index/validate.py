#!/usr/bin/env python3
"""Validates index.json before it reaches a badge.

The platform table below mirrors rom_platform.py in the rom_installer repo.
It is duplicated rather than imported so this repo stays standalone in CI; if
retro-go gains a console, both need the change.
"""

import json
import re
import sys
from pathlib import Path

SUPPORTED_SCHEMA = 1

EXTENSIONS = {
    "nes": (".nes", ".fc", ".fds", ".nsf", ".zip"),
    "gb": (".gb", ".gbc", ".zip"),
    "gbc": (".gbc", ".gb", ".zip"),
    "sms": (".sms", ".sg", ".zip"),
    "gg": (".gg", ".zip"),
    "col": (".col", ".rom", ".zip"),
    "pce": (".pce", ".zip"),
    "lnx": (".lnx", ".zip"),
    "gw": (".gw",),  # retro-go registers Game & Watch without zip support
}

REQUIRED = ("title", "platform", "url", "filename", "licence")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

# GitHub refuses pushes over 100 MB per file and warns past 50 MB. A ROM
# approaching that is the signal to move hosting to release assets — which
# also means teaching the app to follow redirects, since raw.githubusercontent
# does not redirect but release assets do.
SIZE_WARNING = 20 * 1024 * 1024
SIZE_LIMIT = 90 * 1024 * 1024


def problems_with(entry, position):
    where = "catalog[{}]".format(position)
    for field in REQUIRED:
        if not entry.get(field):
            yield "{}: missing '{}'".format(where, field)
    url = entry.get("url", "")
    if url and not url.startswith("https://"):
        yield "{}: url must be https://".format(where)
    platform = entry.get("platform")
    if platform not in EXTENSIONS:
        yield "{}: unknown platform '{}'".format(where, platform)
        return
    filename = entry.get("filename", "")
    if "/" in filename:
        yield "{}: filename must not contain '/'".format(where)
    if not filename.lower().endswith(EXTENSIONS[platform]):
        yield "{}: '{}' is not playable on {}".format(where, filename, platform)
    digest = entry.get("sha256", "")
    if not SHA256.match(digest):
        yield "{}: sha256 must be 64 lowercase hex characters".format(where)
    size = entry.get("size", 0)
    if size > SIZE_LIMIT:
        yield "{}: {} MB exceeds what git will accept; host it as a release asset".format(
            where, size // (1024 * 1024))
    elif size > SIZE_WARNING:
        yield "{}: {} MB is large for git history; consider a release asset".format(
            where, size // (1024 * 1024))


def problems_with_document(document):
    if document.get("schema") != SUPPORTED_SCHEMA:
        yield "schema must be {}".format(SUPPORTED_SCHEMA)
        return
    catalog = document.get("catalog")
    if not isinstance(catalog, list):
        yield "'catalog' must be a list"
        return
    seen = set()
    for position, entry in enumerate(catalog):
        yield from problems_with(entry, position)
        key = (entry.get("platform"), entry.get("filename"))
        if key in seen:
            yield "catalog[{}]: duplicate {}/{}".format(position, key[0], key[1])
        seen.add(key)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.json")
    found = list(problems_with_document(json.loads(path.read_text())))
    for problem in found:
        print(problem)
    entries = len(json.loads(path.read_text()).get("catalog", []))
    print("{}: {} entries, {} problems".format(path, entries, len(found)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
