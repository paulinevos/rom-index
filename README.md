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
index/index.json  (curated, yours)
   └─ pins itch.io game_id + upload_id + sha256 per ROM
        │
badge:  GET itch.io/api/1/<key>/game/<id>/uploads
        GET itch.io/api/1/<key>/upload/<uid>/download   → fresh URL
        stream → verify sha256 → rename into roms/<platform>/
```

itch.io has no browse or search endpoint, so the catalogue must be yours.
itch.io is the file host; `index.json` is the approval list.

## Layout

| File | Role |
| --- | --- |
| `rom_platform.py` | The nine console directories and extensions the launcher browses |
| `rom_destination.py` | SD-vs-flash prefix, `mkdir`, free-space check |
| `catalogue.py` | Fetches and validates `index.json` |
| `catalogue_filter.py` | Narrows to free NES/GB/GBC by default |
| `zip_payload.py` | Enforces retro-go's one-ROM-per-archive rule |
| `itch_api.py` | The two itch.io calls; wraps the API key |
| `rom_download.py` | Streams, hashes, verifies, then commits via rename |
| `rom_installer.py` | LVGL activity |

## Setup

1. Get a **personal** API key at `itch.io/user/settings/api-keys`. OAuth-issued
   keys are rejected by the download endpoints.
2. Install the app, open it, tap the settings row. The key can be scanned as a
   QR code (`InputActivity` offers the camera), which beats typing 40 characters
   on a badge.
3. Point `index_url` at your own index, or edit the default in
   `rom_installer.py`.

## Build and test

```sh
bash bundle.sh                        # -> com.paulinevos.rom_installer_0.1.0.mpk
python3 -m unittest discover -s tests # logic only; stubs mpos, skips lvgl
```

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

- **Redirects.** `DownloadManager` has no redirect handling. If the URL from
  `/upload/<id>/download` 302s to a CDN, downloads will fail and the app needs a
  `Location` follow. Test this first — it is the most likely breakage.
- **URL expiry.** The resolved download URL is probably time-limited, which is
  why it is fetched per install rather than cached. Unconfirmed.
- **`hashlib.sha256`.** Present in most MicroPython builds. `rom_download.py`
  refuses to install rather than skip verification if it is missing.
- **Free-space check** uses `os.statvfs`, which not every port implements.

## Licensing

Only list ROMs whose licence permits redistribution — homebrew, freeware, and
public domain. The `licence` field is required per entry so that curation is
reviewable. Nothing in this code restricts what an index may point at; that
judgement lives in the pull request.
