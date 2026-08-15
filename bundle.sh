#!/usr/bin/env bash
# Builds a deterministic .mpk, per docs.micropythonos.com/apps/bundling-apps/:
# the first ZIP entry must be the top-level directory named after fullname,
# directories sorted before files, stored (-0) rather than deflated.
set -euo pipefail

FULLNAME="com.paulinevos.rom_installer"
VERSION="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "${FULLNAME}/MANIFEST.JSON")"
OUTPUT="${PWD}/${FULLNAME}_${VERSION}.mpk"

cd "$(dirname "$0")"
rm -f "${OUTPUT}"

find "${FULLNAME}" -name '__pycache__' -type d -prune -exec rm -rf {} +

find "${FULLNAME}" -exec touch -t 202501010000.00 {} \;
(find "${FULLNAME}" -type d; find "${FULLNAME}" -type f) \
  | sort \
  | TZ=CET zip -X -r -0 "${OUTPUT}" -@

echo "built ${OUTPUT}"
