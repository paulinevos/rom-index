"""The two itch.io calls needed to turn a catalogue entry into a download URL.

itch.io has no browse or search endpoint, so discovery lives in the curated
index (see catalogue.py). This module only resolves an already-approved
game to the file itch.io is currently serving for it.
"""

import json
import logging

from http_fetch import HttpError, fetch_bytes

logger = logging.getLogger(__name__)


class MissingApiKey(Exception):
    pass


class ItchApiError(Exception):
    pass


class ItchApiKey:
    """An itch.io personal API key.

    OAuth-issued keys are rejected by the download endpoints, so this only
    accepts the personal keys from itch.io/user/settings/api-keys.
    """

    _MINIMUM_LENGTH = 20

    def __init__(self, value):
        stripped = value.strip() if value else ""
        if len(stripped) < self._MINIMUM_LENGTH:
            raise MissingApiKey("an itch.io personal API key is required")
        self._value = stripped

    @classmethod
    def from_preferences(cls, preferences):
        return cls(preferences.get_string("itch_api_key", ""))

    def endpoint(self, path):
        return "https://itch.io/api/1/{}/{}".format(self._value, path)

    def __repr__(self):
        return "<ItchApiKey ...{}>".format(self._value[-4:])


class ItchDownload:

    def __init__(self, url, filename, size):
        self.url = url
        self.filename = filename
        self.size = size


class ItchGame:

    def __init__(self, api_key, game_id):
        self._api_key = api_key
        self._game_id = game_id

    async def resolve(self, upload_id=None, filename=None):
        upload = await self._choose_upload(upload_id, filename)
        url = await self._download_url(upload["id"])
        return ItchDownload(url, upload.get("filename", ""), upload.get("size", 0))

    async def _choose_upload(self, upload_id, filename):
        uploads = await self._uploads()
        if upload_id:
            return self._matching(uploads, "id", upload_id)
        if filename:
            return self._matching(uploads, "filename", filename)
        if len(uploads) != 1:
            raise ItchApiError("game {} has {} uploads; pin one in the index".format(
                self._game_id, len(uploads)))
        return uploads[0]

    async def _uploads(self):
        payload = await self._get("game/{}/uploads".format(self._game_id))
        uploads = payload.get("uploads")
        if not uploads:
            raise ItchApiError("game {} exposes no uploads to this key".format(self._game_id))
        return uploads

    async def _download_url(self, upload_id):
        payload = await self._get("upload/{}/download".format(upload_id))
        url = payload.get("url")
        if not url:
            raise ItchApiError("itch.io returned no download URL for upload {}".format(upload_id))
        return url

    async def _get(self, path):
        # redact_url keeps the API key out of the log, which is otherwise
        # printed in full by DownloadManager.
        try:
            body = await fetch_bytes(self._api_key.endpoint(path), redact_url=True)
        except HttpError as error:
            raise ItchApiError(self._explain(error))
        try:
            payload = json.loads(body)
        except ValueError:
            raise ItchApiError("itch.io returned a response that is not JSON")
        errors = payload.get("errors")
        if errors:
            raise ItchApiError("; ".join(str(error) for error in errors))
        return payload

    @staticmethod
    def _explain(error):
        if error.is_unauthorized():
            # itch.io answers 403 both for a bad key and for an OAuth key,
            # which cannot download; name the second, since it is the trap.
            return ("itch.io rejected the API key (HTTP {}). It must be a "
                    "personal key from itch.io/user/settings/api-keys, not an "
                    "OAuth one.".format(error.status))
        if error.is_not_found():
            return "itch.io has no such game or upload (404); check the index entry"
        return "itch.io request failed: {}".format(error)

    @staticmethod
    def _matching(uploads, field, wanted):
        for upload in uploads:
            if upload.get(field) == wanted:
                return upload
        raise ItchApiError("no upload with {}={}".format(field, wanted))
