#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Create zero-filled stand-ins with the exact sizes of the five firmware assets.
# tests/test_boot_io.c only checks presence and size (it copies bytes into a fake
# volume), so CI can run the boot/app suite without downloading NVIDIA packages.
# Real builds and any hardware run must use scripts/make_assets.py instead.
set -eu
out=${1:-${OUT:-}}
[ -n "$out" ] || { echo "usage: $0 <asset-dir>" >&2; exit 2; }
mkdir -p "$out"
: > "$out/booter_load_ad102.bin"
: > "$out/v67-ad102-610.43.03-four-plm.bin"
: > "$out/gsp_ga10x.bin"
: > "$out/gsp_boot_ad102.bin"
: > "$out/gsp_boot_desc_ad102.bin"
truncate -s 57672 "$out/booter_load_ad102.bin"
truncate -s 64000 "$out/v67-ad102-610.43.03-four-plm.bin"
truncate -s 84277400 "$out/gsp_ga10x.bin"
truncate -s 36864 "$out/gsp_boot_ad102.bin"
truncate -s 84 "$out/gsp_boot_desc_ad102.bin"
echo "placeholder assets written to $out (sizes only, not for hardware use)"
