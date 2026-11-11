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


def main():
    parser = argparse.ArgumentParser(description="生成可复制到 FAT32 U 盘的分阶段目录")
    parser.add_argument("--build", default="build", help="存放 EFI 的目录")
    parser.add_argument("--assets", default="assets", help="五个固件资产所在目录")
    parser.add_argument("--out", default="stick", help="输出目录")
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS),
                        help="只生成指定阶段，可重复；默认生成全部可用阶段")
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent

    def resolve(value):
        path = pathlib.Path(value)
        return path if path.is_absolute() else (repo / path).resolve()

    build = resolve(args.build)
    assets = resolve(args.assets)
    out = resolve(args.out)

    selected = {k: VARIANTS[k] for k in (args.variant or VARIANTS)}
    # auto is opt-in at build time: skip it when it was not built, but a stage
    # the caller named explicitly must exist.
    if not args.variant:
        selected = {k: v for k, v in selected.items() if (build / v[0]).is_file()}
    for image, _ in selected.values():
        if not (build / image).is_file():
            parser.exit(1, f"缺少 {build / image}\n")
    if not selected:
        parser.exit(1, f"{build} 里没有可用的 EFI\n")
    for name in ASSETS:
        if not (assets / name).is_file():
            parser.exit(1, f"缺少 {assets / name}\n")

    if out.exists():
        shutil.rmtree(out)

    for variant, (image, purpose) in selected.items():
        root = out / variant
        (root / "EFI" / "BOOT").mkdir(parents=True)
        (root / "GPU4090-ASSETS").mkdir(parents=True)
        shutil.copy2(build / image, root / "EFI" / "BOOT" / "BOOTX64.EFI")
        for name in ASSETS:
            shutil.copy2(assets / name, root / "GPU4090-ASSETS" / name)
        lines = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}")
        with (root / "SHA256SUMS").open("w", encoding="ascii", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
        print(f"{root}  <- {image}  ({purpose})")

    print(f"\n把某个变体目录里的内容复制到 FAT32 U 盘根目录（一次只放一个），"
          f"开机进启动菜单选 UEFI USB。共 {len(VARIANTS)} 个变体。")


if __name__ == "__main__":
    main()