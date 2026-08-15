# ROM Installer

A MicroPythonOS app for the Fri3d Camp Badge 2026 that installs curated homebrew ROMs from 
into `/roms/<platform>/` on the file system, where
[Retro Core Launcher](https://github.com/MicroPythonOS/MicroPythonOS/tree/main/internal_filesystem/apps/com.micropythonos.retrocore_launcher)
finds them.

Normally, they'd have to be copied over USB. This app allows you to publish ROMs on GitHub and have them installed over Wi-Fi.

## Adding your own ROM

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Build and test

```sh
bash bundle.sh                        # -> com.paulinevos.rom_installer_0.1.0.mpk
python3 -m unittest discover -s tests # logic only; stubs mpos, skips lvgl
```

## Licensing

Only list ROMs whose licence permits redistribution — homebrew, freeware, and
public domain. The `licence` field is required per entry so that curation is
reviewable.
