#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compare a build-result.json with the recorded reference hashes.

The reference file records the images that were verified on hardware, so a
mismatch means the source no longer reproduces them.

Usage: python tools/check_reference_build.py [BUILD_JSON] [REFERENCE_JSON]
"""
import json
import pathlib
import sys

DEFAULT_BUILD = "build/build-result.json"
DEFAULT_REFERENCE = "docs/reference-build-result.json"


def load(path):
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def compare(build, ref):
    bad, checked = [], 0
    for name, want in sorted(ref.items()):
        if name == "zig":
            continue
        have = build.get(name)
        if have is None:
            bad.append(f"{name}: missing from this build")
            continue
        checked += 1
        if have["sha256"] != want["sha256"]:
            bad.append(f"{name}: {have['sha256']} != {want['sha256']}")
        elif have.get("bytes") not in (None, want.get("bytes")):
            bad.append(f"{name}: size {have['bytes']} != {want.get('bytes')}")
    for name in build:
        if name != "zig" and name not in ref:
            print(f"note: {name} is not in the reference set")
    return bad, checked


def main(argv):
    build_path = argv[1] if len(argv) > 1 else DEFAULT_BUILD
    ref_path = argv[2] if len(argv) > 2 else DEFAULT_REFERENCE
    try:
        build = load(build_path)
        ref = load(ref_path)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read inputs: {exc}", file=sys.stderr)
        return 2
    bad, checked = compare(build, ref)
    if bad:
        print("\n".join(bad))
        print("reference build mismatch")
        return 1
    print(f"{checked} recorded images reproduced byte-for-byte")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
