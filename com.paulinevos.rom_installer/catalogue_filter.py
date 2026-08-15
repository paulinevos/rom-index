"""Narrows the catalogue to what this badge should offer.

A shared index may list far more than one device wants to show. Filtering on
the badge rather than in the index keeps the index reusable across devices.
"""

DEFAULT_PLATFORMS = ("nes", "gb", "gbc")


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

    def describe(self):
        consoles = "/".join(platform.upper() for platform in self._platforms)
        return "free {}".format(consoles) if self._free_only else consoles
