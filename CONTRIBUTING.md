# Contributing a ROM

`index/index.json` is the whitelist: an entry there is installable from the
app, anything else is not. Adding a ROM means committing the file and adding
its entry, in one pull request.

Only contribute ROMs whose licence permits redistribution — your own games,
homebrew whose author allows it, freeware, or public domain. See "Licensing" in
the [README](README.md).

## The quick way

```sh
python3 index/add_rom.py ~/Downloads/katkrat.gb \
    --title Katkrat --author SevenLuchtveer \
    --platform gbc --licence author-permitted \
    --source-page https://sevenluchtveer.itch.io/katkrat
```

This copies the ROM into `roms/`, works out `filename`, `size`, `sha256` and
the raw URL, and appends the entry. Then commit both the ROM and the changed
`index/index.json`.

`--price` (in cents) marks a paid game; omit it for free. `--art-url` adds box
art. `--branch` and `--url-base` override the derived URL.

## By hand

1. Commit the ROM to `roms/`. Its extension must match the platform — see the
   table below.
2. Add an entry to `index/index.json` with `url` pointing at the file's raw
   address:

```json
{
  "title": "Your Title",
  "author": "Your Name",
  "licence": "author-permitted",
  "platform": "gbc",
  "url": "https://raw.githubusercontent.com/paulinevos/rom-index/main/roms/your-file.gb",
  "source_page": "https://github.com/username/repo",
  "filename": "your-file.gb",
  "size": 131072,
  "sha256": "4236026d1dd5197164c1009191a159e7a3d495bc0d63002f5a7cfddc58846195",
  "free": true
}
```

`title`, `author`, `platform`, `url`, `filename`, `licence` and `sha256` are
required. `url` must be `https://`. `source_page` is attribution only and is
never fetched. Absent `free`/`price` means free.

```sh
shasum -a 256 roms/your-file.gb          # the sha256 the app checks against
python3 index/validate.py index/index.json
```

The app verifies the hash of what it downloads against `sha256` and discards
the file if they differ, so a wrong hash means nobody can install the ROM.

## Platforms

`platform` is also the directory the ROM installs into (`roms/gbc/`), and the
file's extension has to be one the console accepts:

| `platform` | Console | Accepted extensions |
| --- | --- | --- |
| `nes` | Nintendo Entertainment System | `.nes` `.fc` `.fds` `.nsf` `.zip` |
| `gb` | Gameboy | `.gb` `.gbc` `.zip` |
| `gbc` | Gameboy Color | `.gbc` `.gb` `.zip` |
| `sms` | Sega Master System | `.sms` `.sg` `.zip` |
| `gg` | Sega Game Gear | `.gg` `.zip` |
| `col` | ColecoVision | `.col` `.rom` `.zip` |
| `pce` | PC Engine | `.pce` `.zip` |
| `lnx` | Atari Lynx | `.lnx` `.zip` |
| `gw` | Game & Watch | `.gw` |

## Box art

Optional. `art_url` should be a PNG; it installs to `romart/<platform>/` named
after the ROM without its extension, which is the filename-based form retro-go
looks for first.

## CI checks

Every pull request runs `index/validate.py` and the test suite, which together
check the schema, required fields, `https://` URLs, platform/extension match,
duplicate filenames, file size, and that every indexed ROM exists in `roms/`
with the stated hash and size.

Run both locally before pushing:

```sh
python3 index/validate.py index/index.json
python3 -m unittest discover -s tests
```
