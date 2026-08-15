"""Narrows the catalogue to what this badge should offer.

A shared index may list more consoles than one device wants to show. Filtering
on the badge rather than in the index keeps the index reusable across devices.
"""

from rom_platform import RomPlatform

# Every console the launcher browses. Taken from RomPlatform so a console
# added there is offered here without a second edit.
DEFAULT_PLATFORMS = RomPlatform.all_subdirectories()


class CatalogueFilter:

    def __init__(self, platforms=DEFAULT_PLATFORMS):
        self._platforms = tuple(platforms)

    @classmethod
    def from_preferences(cls, preferences):
        return cls(preferences.get_list("platforms", list(DEFAULT_PLATFORMS)))

    def allows(self, entry):
        return entry.platform.subdirectory in self._platforms

    def describe_roms(self):
        """A noun phrase for the status line, e.g. 'NES/GB ROMs'."""
        if self._covers_every_console():
            return "ROMs"
        return "{} ROMs".format(
            "/".join(platform.upper() for platform in self._platforms))

    def _covers_every_console(self):
        return set(self._platforms) == set(DEFAULT_PLATFORMS)
