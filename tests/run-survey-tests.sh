#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(dirname "$here")
out=${OUT:-$(mktemp -d)}
mkdir -p "$out"
cc=${CC:-gcc}
flags="-std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-parameter -fshort-wchar \
 -D__KERNEL__ -DGU_UEFI_PORT -DGU_4090_DRYRUN -DGU_2820_SURVEY -DGU_ENTRY_LATCHED_SS1_FULL \
 -I$root/compat -I$root/vendor/edk2/Include -I$root/vendor/edk2/Include/X64"
# shellcheck disable=SC2086
$cc $flags "$here/test_survey_config.c" "$root/checks.c" -o "$out/test-survey-config"
"$out/test-survey-config"
