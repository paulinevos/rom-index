"""Covers the HTTP failures that previously escaped as bare RuntimeErrors.

DownloadManager reports every non-2xx as RuntimeError("HTTP nnn"), which no
caller was catching; the catalogue screen hung on "Loading..." instead.
"""

import asyncio
import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: F401  installs the mpos stub and app import path
from support import FakeDownloadManager

from catalogue import Catalogue, CatalogueError  # noqa: E402
from http_fetch import HttpError, fetch_bytes  # noqa: E402


def run(coroutine):
    return asyncio.new_event_loop().run_until_complete(coroutine)


class HttpFetchTest(unittest.TestCase):

    def tearDown(self):
        FakeDownloadManager.reset()

    def test_recovers_the_status_from_the_runtime_error(self):
        FakeDownloadManager.raises = RuntimeError("HTTP 404")
        with self.assertRaises(HttpError) as caught:
            run(fetch_bytes("https://example.test/index.json"))
        self.assertTrue(caught.exception.is_not_found())

    def test_treats_401_and_403_as_unauthorized(self):
        for status in (401, 403):
            FakeDownloadManager.raises = RuntimeError("HTTP {}".format(status))
            with self.assertRaises(HttpError) as caught:
                run(fetch_bytes("https://example.test/x"))
            self.assertTrue(caught.exception.is_unauthorized())

    def test_keeps_the_text_of_a_non_http_runtime_error(self):
        FakeDownloadManager.raises = RuntimeError("socket blew up")
        with self.assertRaises(HttpError) as caught:
            run(fetch_bytes("https://example.test/x"))
        self.assertEqual(caught.exception.status, 0)
        self.assertIn("socket blew up", str(caught.exception))


class CatalogueFetchTest(unittest.TestCase):

    def tearDown(self):
        FakeDownloadManager.reset()

    def test_a_missing_index_names_the_setting_to_fix(self):
        FakeDownloadManager.raises = RuntimeError("HTTP 404")
        with self.assertRaises(CatalogueError) as caught:
            run(Catalogue.fetch("https://example.test/index.json"))
        self.assertIn("index_url", str(caught.exception))

    def test_a_served_index_still_parses(self):
        FakeDownloadManager.returns = b'{"schema": 1, "catalog": []}'
        self.assertTrue(run(Catalogue.fetch("https://example.test/i.json")).is_empty())



if __name__ == "__main__":
    unittest.main()
