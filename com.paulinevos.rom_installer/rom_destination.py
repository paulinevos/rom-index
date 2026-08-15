"""Resolves where on the device a ROM for a given platform belongs."""

import os


class RomDestination:

    ROM_DIRECTORY = "roms"
    ART_DIRECTORY = "romart"

    def __init__(self, platform, storage_prefix):
        self.platform = platform
        self._prefix = storage_prefix

    @classmethod
    def on_preferred_storage(cls, platform):
        # RetroGoLauncher reads from the SD card when one is mounted and from
        # internal flash otherwise. Resolving it the same way, at the same
        # moment, is what keeps an installed ROM visible to the launcher.
        from mpos import SDCardManager

        SDCardManager.mount()
        mount_point = SDCardManager.get_mount_point()
        return cls(platform, mount_point + "/" if mount_point else "")

    def rom_path(self, filename):
        return self._platform_directory(self.ROM_DIRECTORY) + "/" + filename

    def art_path(self, filename):
        return self._platform_directory(self.ART_DIRECTORY) + "/" + filename

    def prepare(self):
        self._make_directory(self._prefix + self.ROM_DIRECTORY)
        self._make_directory(self._platform_directory(self.ROM_DIRECTORY))
        self._make_directory(self._prefix + self.ART_DIRECTORY)
        self._make_directory(self._platform_directory(self.ART_DIRECTORY))

    def free_bytes(self):
        statistics = os.statvfs(self._prefix if self._prefix else "/")
        return statistics[0] * statistics[3]

    def describe(self):
        return self._platform_directory(self.ROM_DIRECTORY)

    def _platform_directory(self, kind):
        return self._prefix + kind + "/" + self.platform.subdirectory

    @staticmethod
    def _make_directory(path):
        try:
            os.mkdir(path)
        except OSError:
            pass  # already there, or the parent is missing and the caller will fail louder
