#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Build the RTX 4070 Laptop (10de:2820) UEFI images with zig 0.14.1.

No GPU access and no installation. Images are PE-checked and reproducible.

Always built:
  SURVEY2820.EFI   read-only discovery for any single 10de:2820
  DRYRUN2820.EFI   exact target admission; every write/DMA/FLR gate closed
  RELTEST2820.EFI  exact target display release + reconnect; still no GPU write
  UNLOCKM2820.EFI  exact target real transaction, manual U confirmation

Only with --with-auto:
  UNLOCKA2820.EFI  same transaction, runs automatically after the countdown

Usage: python build.py [--zig zig] [--out build] [--with-auto]
"""
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

SOURCES = ['app', 'boot_io', 'release', 'port', 'compat', 'checks', 'profile', 'sha256', 'runtime', 'format',
           'vendor/unlock_610', 'vendor/prep_610', 'vendor/layout_610', 'vendor/vbios_610', 'vendor/gfw_eval']
COMMON = ['-target', 'x86_64-uefi', '-std=c11', '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
          '-mno-red-zone', '-fshort-wchar', '-Os', '-g0', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
          '-Wno-misleading-indentation', '-D__KERNEL__', '-DGU_UEFI_PORT', '-DGU_FIRMWARE_BUILD',
          '-DGU_ENTRY_LATCHED_SS1_FULL',
          '-Icompat', '-Ivendor/edk2/Include', '-Ivendor/edk2/Include/X64']

# name, build id, extra defines. The build id is the only string that differs
# between the two real-transaction images.
SAFE_VARIANTS = [('SURVEY2820', 'survey', ['-DGU_4090_DRYRUN', '-DGU_2820_SURVEY']),
                 ('DRYRUN2820', 'dryrun', ['-DGU_4090_DRYRUN']),
                 ('RELTEST2820', 'reltest', ['-DGU_4090_DRYRUN', '-DGU_4090_RELCHECK']),
                 ('UNLOCKM2820', 'manual', ['-DGU_AD104_TRANSACTION', '-DGU_MANUAL'])]
AUTO_VARIANTS = [('UNLOCKA2820', 'auto', ['-DGU_AD104_TRANSACTION'])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zig', default=os.environ.get('ZIG', 'zig'))
    ap.add_argument('--out', default='build')
    ap.add_argument('--with-auto', action='store_true',
                    help='also build UNLOCKA2820.EFI, which unlocks without a key press')
    a = ap.parse_args()
    root = Path(__file__).resolve().parent
    os.chdir(root)
    out = Path(a.out)
    (out / 'obj').mkdir(parents=True, exist_ok=True)
    zig_version = subprocess.check_output([a.zig, 'version'], text=True).strip()
    if zig_version != '0.14.1':
        print(f'warning: tested with zig 0.14.1, found {zig_version}', file=sys.stderr)
    spec = importlib.util.spec_from_file_location('pecheck', root / 'tools' / 'pe_format.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load tools/pe_format.py')
    pe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pe)
    variants = SAFE_VARIANTS + (AUTO_VARIANTS if a.with_auto else [])
    report = {}
    for name, ident, defines in variants:
        objs = []
        for s in SOURCES:
            o = out / 'obj' / f'{name}-{s.replace("/", "_")}.o'
            subprocess.run([a.zig, 'cc', *COMMON, *defines, f'-DGU_BUILD_ID="{ident}"', '-c', f'{s}.c', '-o', str(o)], check=True)
            objs.append(str(o))
        efi = out / f'{name}.EFI'
        # -s: no debug directory; /Brepro: no wall-clock PE timestamp, so the image is byte-for-byte reproducible
        subprocess.run([a.zig, 'cc', '-target', 'x86_64-uefi', '-nostdlib', '-s', '-Wl,/Brepro', *objs, '-o', str(efi)], check=True)
        for extra in (out / f'{name}.pdb', out / f'{name}.lib'):
            extra.unlink(missing_ok=True)
        data = efi.read_bytes()
        pe.validate_pe(data)
        report[efi.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    report['zig'] = zig_version
    (out / 'build-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
