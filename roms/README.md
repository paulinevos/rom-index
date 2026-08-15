# roms

Approved ROM files, served to the badge from
`https://raw.githubusercontent.com/paulinevos/rom-index/main/roms/{platform}/<file>`.

Add a file here, then add a matching entry to `../index/index.json` with its
`sha256` (`shasum -a 256 <file>`). A file here that is not in the index is not
installable; the index is the whitelist.

Only files whose licence permits redistribution belong here.
