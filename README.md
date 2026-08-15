# ROM Installer

A MicroPythonOS app that installs curated homebrew ROMs from itch.io into
`/roms/<platform>/`, where
[Retro Core Launcher](https://github.com/MicroPythonOS/MicroPythonOS/tree/main/internal_filesystem/apps/com.micropythonos.retrocore_launcher)
finds them.

## Why an app and not a payload .mpk

`AppManager.install_mpk` streams an `.mpk` through `StreamingUnzip` with a strict
spec — a single top-level directory named after `fullname`, extracted into
`apps/<fullname>`. An archive cannot write to `/roms`. At runtime there is no
such restriction, which is how the launcher itself creates those directories.

## How it works

```
index/index.json  (the whitelist, yours)
   └─ approved ROM: direct https:// url + sha256
        │
badge:  GET <url>  →  verify sha256  →  check zip  →
        rename into roms/<platform>/
```

`index.json` is the whitelist: an entry there is installable, anything else is
not. The badge does one plain GET per ROM. No API keys, no sessions, no
signed URLs.

### Why not the itch.io API

The API needs a personal key per user, and OAuth keys are rejected for
downloads. The public web flow gets further — `POST /download_url` with an
`upload_id` returns a link with no key and no CSRF token — but that link is an
HTML page rather than the file, the real download needs a scraped CSRF token
plus session cookies, and the signed URL expires in about 30 seconds. None of
that belongs on a badge. Approved ROMs are published as static files instead
and the URL goes in the whitelist.

## Layout

| File | Role |
| --- | --- |
| `rom_platform.py` | The nine console directories and extensions the launcher browses |
| `rom_destination.py` | SD-vs-flash prefix, `mkdir`, free-space check |
| `catalogue.py` | Fetches and validates `index.json` |
| `catalogue_filter.py` | Narrows to free NES/GB/GBC by default |
| `zip_payload.py` | Enforces retro-go's one-ROM-per-archive rule |
| `http_fetch.py` | Turns DownloadManager HTTP failures into typed errors |
| `rom_download.py` | Streams, hashes, verifies, then commits via rename |
| `rom_installer.py` | LVGL activity |

## Publishing a ROM

Commit the file to `roms/` in this repo and point `url` at its raw address:

```
https://raw.githubusercontent.com/paulinevos/rom-index/main/roms/katkrat.gb
```

`raw.githubusercontent.com` serves the bytes directly — **HTTP 200 with no
redirect**, unlike a release asset, which 302s to `objects.githubusercontent.com`
and would need redirect handling the app does not have. ROMs for these consoles
are tens to hundreds of kilobytes, so keeping them in git is cheap.

Only publish what the licence permits: your own games, or homebrew whose author
allows redistribution. Where it does not, list nothing and point people at
`source_page` instead.

## Build and test

```sh
bash bundle.sh                        # -> com.paulinevos.rom_installer_0.1.0.mpk
python3 -m unittest discover -s tests # logic only; stubs mpos, skips lvgl
```

## The catalogue

`index/index.json` is the whitelist. It is served to the badge from
`raw.githubusercontent.com/paulinevos/rom-index/main/index/index.json`.

**It is currently empty.** The app will report "No free NES/GB/GBC ROMs in the
catalogue" until entries are curated.

Adding one means a pull request appending to `catalog`:

```json
{
  "title": "Katkrat",
  "author": "SevenLuchtveer",
  "licence": "author-permitted",
  "platform": "gb",
  "url": "https://raw.githubusercontent.com/paulinevos/rom-index/main/roms/katkrat.gb",
  "source_page": "https://sevenluchtveer.itch.io/katkrat",
  "filename": "katkrat.gb",
  "size": 131072,
  "sha256": "…64 hex chars…",
  "free": true,
  "art_url": "https://…/katkrat.png"
}
```

`title`, `platform`, `url`, `filename`, `licence` and `sha256` are required.
`url` must be `https://`. `source_page` is attribution only and is never
fetched. Absent `free`/`price` means free.

```sh
shasum -a 256 the-file-you-published    # find sha256
python3 index/validate.py index/index.json
```

`validate.py` mirrors the platform table in `rom_platform.py`; if retro-go
gains a console, both need the change.

## Filtering

By default only **free NES, GB and GBC** entries are shown. Both parts are
preferences, so a shared index stays reusable:

```json
{ "platforms": ["nes", "gb", "gbc"], "free_only": true }
```

An entry counts as free when it sets `"free": true`, or sets `"price": 0`, or
states neither.

## Constraints inherited from retro-go

Checked against [ducalex/retro-go](https://github.com/ducalex/retro-go):

- **ZIPs must contain exactly one ROM and nothing else.** `zip_payload.py`
  enforces this at install time, because itch.io uploads usually bundle a
  readme. It matters twice over: MicroPythonOS's `get_zip_crc32` reads only the
  first local header, so a multi-file archive also yields the wrong CRC32 and
  the wrong box art.
- **Game & Watch takes no `.zip`** — `applications.c` registers it as `gw`
  alone. Every other console accepts zip.
- **Box art is filename-based without the ROM extension**
  (`/romart/nes/Super Mario.png`), which is what this app writes. The CRC32
  form is much slower and is not used here.
- Large ROMs inside a zip may still fail to load on low-memory devices. That is
  a runtime limit no installer can check for.

## Not yet verified on hardware

These are the parts I could not exercise from a desktop:

- **Redirects.** `DownloadManager` has no redirect handling. Serving ROMs from
  `raw.githubusercontent.com` avoids the issue (200, no redirect), so this only
  bites if an entry points somewhere that does redirect. Keep `url` on raw
  GitHub and it stays a non-problem.
- **`hashlib.sha256`.** Present in most MicroPython builds. `rom_download.py`
  refuses to install rather than skip verification if it is missing.
- **Free-space check** uses `os.statvfs`, which not every port implements.

## Licensing

Only list ROMs whose licence permits redistribution — homebrew, freeware, and
public domain. The `licence` field is required per entry so that curation is
reviewable. Nothing in this code restricts what an index may point at; that
judgement lives in the pull request.
