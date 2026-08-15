"""Streams a ROM to its destination, verifying it before it becomes visible."""

import binascii
import hashlib
import logging
import os

from mpos import DownloadManager

from rom_destination import RomDestination
from zip_payload import NotAUsableArchive, ZipPayload

logger = logging.getLogger(__name__)


class InstallFailed(Exception):
    pass


class RomDownload:

    PARTIAL_SUFFIX = ".part"

    def __init__(self, entry, progress_reporter):
        self._entry = entry
        self._report = progress_reporter

    async def install(self):
        destination = RomDestination.on_preferred_storage(self._entry.platform)
        destination.prepare()
        target = destination.rom_path(self._entry.filename)
        self._refuse_if_present(target)
        self._refuse_if_too_large(destination, self._entry.size)

        partial = target + self.PARTIAL_SUFFIX
        await self._stream_to(partial)
        self._check_archive(partial)
        os.rename(partial, target)
        await self._install_art(destination)
        return destination.describe()

    async def _stream_to(self, partial_path):
        digest = self._new_digest()
        handle = open(partial_path, "wb")
        try:
            await self._pump(handle, digest)
        except Exception as error:
            handle.close()
            self._discard(partial_path)
            raise InstallFailed("download failed: {}".format(error))
        handle.close()
        self._verify(partial_path, digest)

    async def _pump(self, handle, digest):
        async def write_chunk(chunk):
            handle.write(chunk)
            if digest:
                digest.update(chunk)

        async def show_percent(percent):
            await self._report("Downloading {:.0f}%".format(percent))

        await DownloadManager.download_url(
            self._entry.url,
            total_size=self._entry.size or None,
            chunk_callback=write_chunk,
            progress_callback=show_percent,
        )

    def _check_archive(self, partial_path):
        if not self._entry.filename.lower().endswith(".zip"):
            return
        try:
            payload = ZipPayload.read_from(partial_path)
            payload.must_be_playable_on(self._entry.platform)
        except NotAUsableArchive as error:
            self._discard(partial_path)
            raise InstallFailed(str(error))

    def _verify(self, partial_path, digest):
        if not digest:
            return
        actual = binascii.hexlify(digest.digest()).decode()
        if actual == self._entry.sha256.lower():
            return
        self._discard(partial_path)
        raise InstallFailed("checksum mismatch: the file served is not the approved one")

    def _new_digest(self):
        if not self._entry.sha256:
            return None
        try:
            return hashlib.sha256()
        except AttributeError:
            # Refusing beats installing an unverified binary from a URL we
            # only reached by way of a third party's redirect.
            raise InstallFailed("this build has no sha256; cannot verify the ROM")

    async def _install_art(self, destination):
        if not self._entry.art_url:
            return
        art_name = self._entry.filename.rsplit(".", 1)[0] + ".png"
        try:
            await self._report("Fetching box art...")
            await DownloadManager.download_url(
                self._entry.art_url, outfile=destination.art_path(art_name))
        except Exception as error:
            # Art is decoration; the ROM is already installed and playable.
            logger.warning("box art for %s failed: %s", self._entry.title, error)

    def _refuse_if_present(self, target):
        try:
            os.stat(target)
        except OSError:
            return
        raise InstallFailed("{} is already installed".format(self._entry.filename))

    def _refuse_if_too_large(self, destination, size):
        needed = size or self._entry.size
        if needed and needed > destination.free_bytes():
            raise InstallFailed("needs {} KB but only {} KB free".format(
                needed // 1024, destination.free_bytes() // 1024))

    @staticmethod
    def _discard(path):
        try:
            os.remove(path)
        except OSError as error:
            logger.warning("could not remove %s: %s", path, error)
