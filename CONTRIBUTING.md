# Contributing a ROM

`index/index.json` is the whitelist: an entry there is installable from the
app, anything else is not.

Only contribute ROMs whose licence permits redistribution — your own games,
homebrew whose author allows it, freeware, or public domain.

## Two ways to publish

| | Where the file lives | Your pull request |
| --- | --- | --- |
| **1. Self-hosted** | your own server | one entry in `index/index.json` |
| **2. In this repo** | `roms/` | the ROM plus its entry |

Both install identically. Self-hosting keeps your binary out of this repo's
history; contributing it here means the file cannot rot.

### 1. Self-hosted

```sh
python3 index/add_rom.py --url https://example.com/roms/your-title.gb \
    --title "Some Title" --author YourName \
    --platform gbc --licence author-permitted
```

It fetches the file, so `sha256` and `size` describe what a badge will really
receive. Three things to know:

- **The URL must not redirect.** The badge cannot follow one. This rules out
  GitHub release assets, S3 pre-signed links and most `http`→`https` setups.
- **Serve the exact bytes.** If the file changes, the app discards the download
  and names your host — nobody is handed a file you did not approve.
- **If your host goes away**, the entry stops working and the app says it could
  not reach it. Nobody will chase you, so keep an eye on your entries.

### 2. In this repo

```sh
python3 index/add_rom.py ~/your-roms/your-title.gb \
    --title "Some Title" --author YourName \
    --platform gbc --licence author-permitted \
    --source-page https://github.com/username/repo
```

Copies the ROM into `roms/` and points `url` at its raw address. Commit both.

`--art-url` adds box art. `--source-page` is attribution only, never fetched.

## The entry

Either command writes this for you; by hand it looks like:

```json
{
  "title": "Your Title",
  "author": "Your Name",
  "licence": "author-permitted",
  "platform": "gbc",
  "url": "https://raw.githubusercontent.com/paulinevos/rom-index/main/roms/your-file.gb",
  "filename": "your-file.gb",
  "size": 131072,
  "sha256": "4236026d1dd5197164c1009191a159e7a3d495bc0d63002f5a7cfddc58846195"
}
```

`title`, `author`, `platform`, `url`, `filename`, `licence` and `sha256` are
required; `url` must be `https://`. A wrong hash means nobody can install the
ROM, since the app discards anything that does not match.

## Platforms

`platform` is also the directory the ROM installs into (`roms/gbc/`), and the
extension has to be one the console accepts:

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

A `.zip` must contain exactly one ROM and nothing else — retro-go refuses
anything more, and the app rejects such an archive at install time.

Box art is optional: `art_url` should be a PNG, installed to
`romart/<platform>/` named after the ROM without its extension.

## Checks

Run before pushing; CI runs the same:

```sh
python3 index/validate.py index/index.json    # schema, fields, platforms
python3 index/check_urls.py index/index.json  # every url, hash, no redirects
python3 -m unittest discover -s tests         # offline suite
```
