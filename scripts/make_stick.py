#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Lay out a FAT32 USB drive for the RTX 4070 Laptop unlock.

Two layouts:

  auto (default)  one plug-and-unlock stick. The root image is UNLOCKA2820.EFI,
                  so a cold boot from this stick unlocks after 3 s. The other
                  images sit in RECOVERY/ and can be copied over the root image.
  staged          one directory per stage (survey, dryrun, reltest, unlockm,
                  auto); copy the contents of one directory to the stick root.

Usage:
  python scripts/make_stick.py --build build --assets assets --out stick
  python scripts/make_stick.py --layout staged --out stick
  python scripts/make_stick.py --variant dryrun --out stick
"""
import argparse
import hashlib
import pathlib
import shutil

ASSETS = [
    "booter_load_ad102.bin",
    "v67-ad102-610.43.03-four-plm.bin",
    "gsp_ga10x.bin",
    "gsp_boot_ad102.bin",
    "gsp_boot_desc_ad102.bin",
]
VARIANTS = {
    "survey": ("SURVEY2820.EFI", "任意单张 10de:2820 的只读调查；不释放显示、不写 GPU"),
    "dryrun": ("DRYRUN2820.EFI", "精确目标准入预检；不释放显示、不写 GPU"),
    "reltest": ("RELTEST2820.EFI", "释放并重连显示驱动；不写 GPU；启动后按 U"),
    "unlockm": ("UNLOCKM2820.EFI", "真实手动事务；仅在前两阶段通过后启动并按 U"),
    "auto": ("UNLOCKA2820.EFI", "真实自动事务；倒计时结束即解锁，Esc/S 可跳过"),
}
RECOVERY_NAMES = {
    "auto": "UNLOCK-AUTO-2820.EFI",
    "unlockm": "UNLOCK-MANUAL-2820.EFI",
    "reltest": "RELTEST-2820.EFI",
    "dryrun": "DRYRUN-2820.EFI",
    "survey": "SURVEY-2820.EFI",
}
STICK_README = """\
RTX 4070 Laptop (10de:2820) plug-and-unlock stick
=================================================

ACTIVE IMAGE: UNLOCKA2820.EFI (automatic, 3 second countdown)

This stick unlocks only when the firmware BOOTS it. Hot-plugging it into a
running Windows does nothing.

Expected behaviour:
  stick plugged in, cold boot  -> firmware starts this stick, unlocks, Windows
  stick removed, cold boot     -> firmware falls back to Windows Boot Manager

To make the firmware try this stick first, either put it ahead of Windows Boot
Manager in the firmware setup, or register a boot entry with:
  powershell -File scripts\\usb_boot_entry.ps1 -Apply

During the countdown:
  Esc  open the two-entry menu
  S    start Windows without unlocking
  U    unlock immediately

Exact target (all must match, otherwise the image refuses before writing):
  PCI 10de:2820, subsystem 1d05:1297, BDF 0000:01:00.0,
  VBIOS 95.06.15.40.5F FWSEC geometry

Logs: \\GPU4090-UNLOCK\\RUNnnnn.TXT

Recovery:
  - Screen says STOPPED, or no Windows after ~2 minutes: hold the power button
    until the machine is off, remove this stick, boot Windows Boot Manager.
  - A full power-off returns the GPU to stock state.

RECOVERY\\ holds the other images. Copy one over \\EFI\\BOOT\\BOOTX64.EFI to
change mode, then verify with SHA256SUMS.
"""


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_sums(root):
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    with (root / "SHA256SUMS").open("w", encoding="ascii", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")


def copy_assets(assets, root):
    (root / "GPU4090-ASSETS").mkdir(parents=True)
    for name in ASSETS:
        shutil.copy2(assets / name, root / "GPU4090-ASSETS" / name)


def layout_auto(build, assets, out, parser):
    image = build / VARIANTS["auto"][0]
    if not image.is_file():
        parser.exit(1, f"缺少 {image}；先运行 python build.py\n")
    (out / "EFI" / "BOOT").mkdir(parents=True)
    (out / "RECOVERY").mkdir()
    shutil.copy2(image, out / "EFI" / "BOOT" / "BOOTX64.EFI")
    copy_assets(assets, out)
    for key, name in RECOVERY_NAMES.items():
        src = build / VARIANTS[key][0]
        if src.is_file():
            shutil.copy2(src, out / "RECOVERY" / name)
    (out / "README-AUTO.txt").write_text(STICK_README, encoding="utf-8", newline="\n")
    write_sums(out)
    print(f"{out}  <- {VARIANTS['auto'][0]} (自动解锁，根目录即启动镜像)")
    print("把该目录内容复制到 FAT32 U 盘根目录；固件需优先启动该 U 盘。")


def layout_staged(build, assets, out, names, parser):
    selected = {k: VARIANTS[k] for k in (names or VARIANTS)}
    if not names:
        selected = {k: v for k, v in selected.items() if (build / v[0]).is_file()}
    for image, _ in selected.values():
        if not (build / image).is_file():
            parser.exit(1, f"缺少 {build / image}\n")
    if not selected:
        parser.exit(1, f"{build} 里没有可用的 EFI\n")
    for variant, (image, purpose) in selected.items():
        root = out / variant
        (root / "EFI" / "BOOT").mkdir(parents=True)
        shutil.copy2(build / image, root / "EFI" / "BOOT" / "BOOTX64.EFI")
        copy_assets(assets, root)
        write_sums(root)
        print(f"{root}  <- {image}  ({purpose})")
    print(f"\n把某个阶段目录里的内容复制到 FAT32 U 盘根目录（一次只放一个）。共 {len(selected)} 个阶段。")


def main():
    parser = argparse.ArgumentParser(description="生成 FAT32 U 盘目录布局")
    parser.add_argument("--build", default="build", help="存放 EFI 的目录")
    parser.add_argument("--assets", default="assets", help="五个固件资产所在目录")
    parser.add_argument("--out", default="stick", help="输出目录")
    parser.add_argument("--layout", choices=("auto", "staged"), default="auto",
                        help="auto: 根目录即自动解锁镜像；staged: 每个阶段一个目录")
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS),
                        help="staged 布局下只生成指定阶段，可重复")
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent

    def resolve(value):
        path = pathlib.Path(value)
        return path if path.is_absolute() else (repo / path).resolve()

    build = resolve(args.build)
    assets = resolve(args.assets)
    out = resolve(args.out)

    for name in ASSETS:
        if not (assets / name).is_file():
            parser.exit(1, f"缺少 {assets / name}\n")

    if out.exists():
        try:
            shutil.rmtree(out)
        except OSError as exc:
            parser.exit(1, f"无法清空 {out}: {exc}\n")

    if args.layout == "auto":
        if args.variant:
            parser.exit(2, "--variant 只用于 --layout staged\n")
        layout_auto(build, assets, out, parser)
    else:
        layout_staged(build, assets, out, args.variant, parser)


if __name__ == "__main__":
    main()
