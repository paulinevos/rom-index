"""Narrows the catalogue to what this badge should offer.

A shared index may list more than one device wants to show. Filtering on the
badge rather than in the index keeps the index reusable across devices.
"""

from rom_platform import RomPlatform

# Every console the launcher browses. Taken from RomPlatform so a console
# added there is offered here without a second edit.
DEFAULT_PLATFORMS = RomPlatform.all_subdirectories()


class CatalogueFilter:

    def __init__(self, platforms=DEFAULT_PLATFORMS, free_only=True):
        self._platforms = tuple(platforms)
        self._free_only = free_only

    @classmethod
    def from_preferences(cls, preferences):
        platforms = preferences.get_list("platforms", list(DEFAULT_PLATFORMS))
        return cls(platforms, preferences.get_bool("free_only", True))

    def allows(self, entry):
        if entry.platform.subdirectory not in self._platforms:
            return False
        if self._free_only and not entry.is_free:
            return False
        return True

    def describe_roms(self):
        """A noun phrase for the status line, e.g. 'free NES/GB ROMs'."""
        words = []
        if self._free_only:
            words.append("free")
        if not self._covers_every_console():
            words.append("/".join(platform.upper() for platform in self._platforms))
        words.append("ROMs")
        return " ".join(words)

    def _covers_every_console(self):
        return set(self._platforms) == set(DEFAULT_PLATFORMS)
