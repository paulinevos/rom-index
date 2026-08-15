#!/usr/bin/env python3
"""Fetches every catalogue URL and checks it is what the index promises.

ROMs may be self-hosted, so the index can point anywhere. That URL is what a
badge will fetch, and the badge cannot follow redirects: DownloadManager
treats a 3xx as success and writes the redirect body to disk. So this refuses
a redirecting URL outright rather than letting it reach users as a mystifying
checksum mismatch.

    python3 index/check_urls.py index/index.json
"""

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Some hosts sit behind Cloudflare, which answers the default
# "Python-urllib/x.y" agent with 403 before the request reaches the file.
USER_AGENT = "rom-index-check/1.0 (+https://github.com/paulinevos/rom-index)"
TIMEOUT_SECONDS = 30


class RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Turns a redirect into an error instead of quietly following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Signed CDN URLs are enormous; the host is the useful part.
        target = newurl.split("://", 1)[-1].split("/", 1)[0]
        raise urllib.error.HTTPError(
            req.full_url, code,
            "redirects to {} — the badge cannot follow redirects".format(target),
            headers, fp)


def fetch(url):
    opener = urllib.request.build_opener(RefuseRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def problems_with(entry):
    url = entry["url"]
    name = entry.get("filename", url)
    try:
        body = fetch(url)
    except urllib.error.HTTPError as error:
        yield "{}: {} -> HTTP {} {}".format(name, url, error.code, error.reason)
        return
    except (urllib.error.URLError, OSError) as error:
        yield "{}: {} -> unreachable ({})".format(name, url, error)
        return

    digest = hashlib.sha256(body).hexdigest()
    if digest != entry.get("sha256"):
        yield "{}: sha256 is {} but the index says {}".format(
            name, digest, entry.get("sha256"))
    size = entry.get("size")
    if size and len(body) != size:
        yield "{}: served {} bytes but the index says {}".format(name, len(body), size)


def main(argv):
    path = Path(argv[0] if argv else "index/index.json")
    catalog = json.loads(path.read_text())["catalog"]
    found = []
    for entry in catalog:
        problems = list(problems_with(entry))
        found.extend(problems)
        print("{}  {}".format("FAIL" if problems else "ok  ",
                              entry.get("filename", entry["url"])))
        for problem in problems:
            print("      " + problem)
    print("\n{} entries, {} problems".format(len(catalog), len(found)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
