"""Turns DownloadManager's HTTP failures into something callers can act on.

DownloadManager signals every non-2xx/3xx response as `RuntimeError("HTTP nnn")`
and nothing else, so the status has to be recovered from the message. Doing
that in one place keeps the string-parsing contained: if DownloadManager ever
grows a typed error, only this module changes.
"""

import logging

logger = logging.getLogger(__name__)

_PREFIX = "HTTP "


class HttpError(Exception):

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status

    def is_unauthorized(self):
        return self.status in (401, 403)

    def is_not_found(self):
        return self.status == 404


async def fetch_bytes(url, redact_url=False):
    # Resolved per call rather than bound at import, so this module does not
    # capture whichever DownloadManager happened to exist at import time.
    import mpos

    try:
        return await mpos.DownloadManager.download_url(url, redact_url=redact_url)
    except RuntimeError as error:
        raise as_http_error(error)


def as_http_error(error):
    status = _status_from(str(error))
    if status:
        return HttpError(status, "server returned HTTP {}".format(status))
    # Not an HTTP status, so the cause is unknown; keep the original text
    # rather than inventing a status the caller would branch on.
    return HttpError(0, str(error))


def _status_from(message):
    if not message.startswith(_PREFIX):
        return None
    try:
        return int(message[len(_PREFIX):].strip())
    except ValueError:
        return None
