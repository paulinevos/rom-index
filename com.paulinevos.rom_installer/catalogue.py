"""The curated catalogue of installable ROMs.

The list of what may be installed is a JSON document under your own control.
Each entry pins a direct https:// URL for an approved ROM, so curation happens
by pull request against that file. Nothing is discovered at runtime.
"""

import json
import logging

from http_fetch import HttpError, fetch_bytes
from rom_platform import RomPlatform, UnknownPlatform

logger = logging.getLogger(__name__)

SUPPORTED_SCHEMA = 1


class CatalogueError(Exception):
    pass


class CatalogueEntry:

    def __init__(self, record):
        self.title = record["title"]
        self.author = record.get("author", "")
        self.licence = record.get("licence", "unknown")
        self.platform = RomPlatform(record["platform"])
        self.url = self._required_url(record["url"])
        # Where the ROM came from, shown for attribution; never fetched.
        self.source_page = record.get("source_page", "")
        self.filename = self._required_name(record["filename"])
        self.sha256 = record.get("sha256")
        self.size = record.get("size", 0)
        self.art_url = record.get("art_url")
        # An entry stating neither a price nor a `free` flag is taken as
        # free, which is what a homebrew index holds.
        self.is_free = bool(record.get("free", record.get("price", 0) == 0))
        if not self.platform.accepts(self.filename):
            raise CatalogueError(self.platform.rejection_reason(self.filename))

    @staticmethod
    def _required_url(url):
        # Plain HTTPS only: the badge fetches this without a session, so
        # anything needing cookies or a signature would fail at install time.
        if not isinstance(url, str) or not url.startswith("https://"):
            raise CatalogueError("'{}' is not an https:// URL".format(url))
        return url

    @staticmethod
    def _required_name(filename):
        # A path separator here would write outside roms/<platform>/.
        if not isinstance(filename, str) or not filename or "/" in filename:
            raise CatalogueError("'{}' is not a usable filename".format(filename))
        return filename

    def subtitle(self):
        return "{} - {}".format(self.platform.display_name, self.author or self.licence)


class Catalogue:

    def __init__(self, entries):
        self._entries = entries

    @classmethod
    async def fetch(cls, index_url):
        try:
            body = await fetch_bytes(index_url)
        except HttpError as error:
            raise CatalogueError(cls._explain(error))
        return cls.parse(body)

    @staticmethod
    def _explain(error):
        if error.is_not_found():
            return "no catalogue at that URL (404) - check index_url"
        if error.is_unauthorized():
            return "the catalogue URL needs credentials (HTTP {})".format(error.status)
        return str(error)

    @classmethod
    def parse(cls, body):
        document = json.loads(body)
        schema = document.get("schema")
        if schema != SUPPORTED_SCHEMA:
            raise CatalogueError("index schema {} is not supported".format(schema))
        return cls(cls._read_entries(document.get("catalog", [])))

    @staticmethod
    def _read_entries(records):
        entries = []
        for record in records:
            try:
                entries.append(CatalogueEntry(record))
            except (KeyError, CatalogueError, UnknownPlatform) as error:
                # One malformed record should not hide the rest of the catalogue.
                logger.warning("skipping catalogue entry: %s", error)
        entries.sort(key=lambda entry: entry.title.lower())
        return entries

    def for_platform(self, subdirectory):
        return Catalogue([entry for entry in self._entries
                          if entry.platform.subdirectory == subdirectory])

    def matching(self, catalogue_filter):
        return Catalogue([entry for entry in self._entries
                          if catalogue_filter.allows(entry)])

    def platform_names(self):
        seen = []
        for entry in self._entries:
            if entry.platform.subdirectory not in seen:
                seen.append(entry.platform.subdirectory)
        return seen

    def is_empty(self):
        return not self._entries

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]
