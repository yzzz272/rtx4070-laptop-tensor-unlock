# RTX 4070 Laptop tensor-rate unlock (Windows UEFI)

**English** | [简体中文](README.zh-CN.md)

A UEFI application for the **RTX 4070 Laptop GPU (`10de:2820`)** that removes the
half-rate limit on FP16/BF16 tensor math with FP32 accumulation, before Windows
and the NVIDIA driver load.

Does not flash the VBIOS, does not replace the NVIDIA driver, does not modify
Windows system files.

> **AI-generated. Verify before use.** The code, scripts, tests and this document
> were written with substantial AI assistance. They were built and run on the
> machine below, but not reviewed by a security professional. Read the source
> before running it, and do not run it on a machine you cannot afford to lose.

## Verified hardware

| | |
|---|---|
| Laptop | MECHREVO JiguangPro Series GM5AR7O |
| GPU | RTX 4070 Laptop, AD106M, 36 SM |
| PCI / subsystem | `10de:2820` / `1d05:1297` |
| BDF | `0000:01:00.0` |
| VBIOS | `95.06.15.40.5F` |
| Chip | `PMC_BOOT_0=0x196000a1` |
| Driver | NVIDIA 617.42, Windows 10 19045 |

This is the only verified machine. Other RTX 4070 Laptop models differ in
subsystem, BDF, VBIOS and firmware behaviour. Run `SURVEY2820` first on those: it
is read-only, logs the card's identity and FWSEC geometry, and starts Windows.

## Measured result

Same machine, same CUDA probe binary, 8192³ GEMM, median of 20 runs:

| Mode | Stock | Unlocked |
|---|---:|---:|
| FP16 in / FP16 accumulate | 152–158 TF/s | 152–159 TF/s |
| FP16 in / FP32 accumulate | 74–77 TF/s | 144–160 TF/s |
| BF16 in / FP32 accumulate | 74–77 TF/s | 145–158 TF/s |
| TF32 | 38–40 TF/s | 76–80 TF/s |
| FP32 SIMT (control) | 17.6–19.1 TF/s | 17.6–19.1 TF/s |

FP16 accumulate is the control group: it does not move. The FP32-accumulate path
roughly doubles, so the ratio `FP16acc / FP32acc` goes from about `2.0` to about
`1.0`.

Register-side evidence from the boot log:

```text
AD102 before-firmware: readout1=0x410080 fields=0 0 2 0 0 2 0 2 0 valid=1 full=0
selector result: SS0=0x88888888 matched=1
selector result: SS1=0x8 matched=1
AD102 selectors-applied: readout1=0 fields=0 0 0 0 0 0 0 0 0 valid=1 full=1
PCIe FLR returned: result=0
AD102 post-FLR: readout1=0 fields=0 0 0 0 0 0 0 0 0 valid=1 full=1
POST-GOP SS0=0x88888888 SS1=0x8
TRANSACTION OK
```

Full logs: [`docs/logs/RUN0006-success.txt`](docs/logs/RUN0006-success.txt),
[`docs/logs/RUN0001-auto-success.txt`](docs/logs/RUN0001-auto-success.txt),
[`docs/logs/unlocked-tensor-probe.txt`](docs/logs/unlocked-tensor-probe.txt).

The bottleneck after unlocking is power and cooling, not the rate limit: the
115 W budget caps sustained clocks long before the tensor path saturates.

## How it works

Consumer Ada cards run the FP32-accumulate tensor path at half the FP16-accumulate
rate. The limit is set by two volatile speed selectors (`SS0`, `SS1`) and four PLM
permission registers, and only NVIDIA's own signed firmware chain can open them.
Before Windows starts, the application:

1. Reads the card's own VBIOS (`BAR0+0x300000`, 1 MiB) and parses the FWSEC
   descriptor;
2. loads the signed GSP Falcon firmware to establish WPR2;
3. runs the pinned AD102-family Booter and four-PLM payload on SEC2, opening
   `WPR_CFG`, `WPR` and `FEAT_OVR_PLM`;
4. writes `SS0=0x88888888` and `SS1=0x8`, then reads them back;
5. performs one PCIe Function Level Reset and confirms the selectors survived;
6. reconnects the firmware display driver and hands over to the existing Windows
   Boot Manager.

The selectors are volatile: a full power-off restores the original values, so the
transaction runs again on every cold boot. This is not a permanent hardware
modification, and it cannot be made permanent without replacing signed firmware.

## Changes from upstream

| File | Change |
|---|---|
| `target_2820.h` | new: exact target profile — PCI ID, subsystem, BDF, FWSEC geometry |
| `checks.c`, `profile.c`, `port.c` | pin subsystem, BDF and FWSEC geometry; `GU_2820_SURVEY` relaxes them while keeping every write gate closed |
| `app.c` | target `10de:2820`, RTX 4070 Laptop strings |
| `vendor/prep_610.h` | add `GU_AD106M_RTX_4070_LAPTOP 0x2820` to the pinned Booter family |
| `build.py` | five variants; `--safe-only` drops the automatic image |
| `scripts/make_stick.py` | plug-and-unlock layout by default, `--layout staged` for per-stage directories |
| `scripts/usb_boot_entry.ps1` | new: reversible firmware boot entry for the stick |
| `tools/check_reference_build.py` | new: build vs recorded hashes |
| `tests/` | fixtures for this card; survey admission tests |

The write gates are not relaxed anywhere: `SURVEY2820` has no MMIO write, DMA, Bus
Master, PCI config write, display release or FLR path at all, and the four other
images refuse before the first write unless every pinned value matches.

## Requirements

- Windows 10 or 11, UEFI boot, **Secure Boot off** (the images are unsigned)
- Exactly one `10de:2820`
- A USB drive you can erase — FAT32, 128 MB is enough
- Fast Startup off: `powercfg /h off`
- BitLocker suspended if it is on: `Suspend-BitLocker -MountPoint C: -RebootCount 3`
- Python 3, Zig **0.14.1**, and `zstd` on `PATH` to build

## Build

### Reproduce the recorded images

```powershell
python scripts/make_assets.py --out assets
python build.py --zig C:\path\to\zig.exe --out build
python tools/check_reference_build.py
```

The third command compares your build with
[`docs/reference-build-result.json`](docs/reference-build-result.json). This tree
reproduces all five images byte-for-byte, including the two that ran on hardware.
CI runs the same check.

### Build only the safe images

```powershell
python build.py --zig C:\path\to\zig.exe --out build --safe-only
```

Leaves out `UNLOCKA2820`, the only image that unlocks without a key press.

### Firmware assets

`assets/` is generated locally; NVIDIA's files are not redistributed here.

```text
booter_load_ad102.bin                 57672  sha256 6ee05b20e1dc244c...
v67-ad102-610.43.03-four-plm.bin      64000  sha256 44c36b2d6b3424e5...
gsp_ga10x.bin                      84277400  sha256 572373620a37418f...
gsp_boot_ad102.bin                    36864  sha256 45d6335a8185d6ff...
gsp_boot_desc_ad102.bin                  84  sha256 83f8f3f1f5f9496e...
```

`scripts/make_assets.py` downloads the pinned NVIDIA `610.43.03` inputs, verifies
their SHA-256 values and generates these five files.

## Images

| Image | Writes GPU | Display release | Key press |
|---|---:|---:|---|
| `SURVEY2820.EFI` | no | no | none |
| `DRYRUN2820.EFI` | no | no | none |
| `RELTEST2820.EFI` | no | yes | `U` |
| `UNLOCKM2820.EFI` | yes | yes | `U` |
| `UNLOCKA2820.EFI` | yes | yes | none (3 s) |

## USB drive

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
```

Copy the **contents** of `stick\` to the root of a FAT32 USB drive. The root image
is the automatic one; the other four sit in `RECOVERY\`.

```text
EFI/BOOT/BOOTX64.EFI     UNLOCKA2820
GPU4090-ASSETS/          the five firmware files
RECOVERY/                the other four images
README-AUTO.txt
SHA256SUMS
```

`GPU4090-ASSETS` and `GPU4090-UNLOCK` are legacy upstream path names. Renaming
them would change the bytes of the images verified on hardware.

### Plug and unlock

```powershell
# dry run: shows what would change
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1
# create the entry and put it first
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply
```

| State | Result |
|---|---|
| Stick plugged in, cold boot | firmware starts the stick, unlocks, Windows starts |
| Stick removed, cold boot | firmware falls back to Windows Boot Manager, GPU stays stock |

The script acts only when the volume is removable FAT32 with the expected label,
the root image is the released automatic image (SHA-256 checked), Secure Boot is
off, and no entry is already recorded. It stores the entry id in
`%ProgramData%\Rtx4070Unlock\usb-entry.json` so `-Remove -Apply` undoes it exactly.

First boot: shut down fully, wait for the power light to go out, hold the power
button for 10 seconds, then power on and open the boot menu (F7 on the verified
machine). During the countdown, `Esc` opens a menu, `S` starts stock Windows, `U`
unlocks immediately.

A first boot that passes admission logs:

```text
PCI scan: 10de:2820 functions found=1
PCIe device capability=... FLR_capable=1
FWSEC from this card's VBIOS: image_off=0x46888 image_size=0x10300 ...
release preflight: status=0
Checks passed.
```

### Staged verification

For a machine that is not the verified one, do not start with the automatic
image.

```powershell
python scripts/make_stick.py --layout staged --out stick
```

1. `SURVEY2820` — read-only. Send `\GPU4090-UNLOCK\RUNnnnn.TXT` for review.
2. `DRYRUN2820` — exact target only. Expect `Checks passed.`
3. `RELTEST2820` — press `U`. Expect `release test: status=0 gop=1`.
4. `UNLOCKM2820` — press `U`. Expect `TRANSACTION OK`.

## Verify

```powershell
python tools/check_reference_build.py
nvidia-smi
```

Throughput: compare FP16-accumulate against FP32-accumulate with the same binary.
Stock is about `2.0`, unlocked about `1.0`. Also check the Windows system log for
`nvlddmkm`, `Display` or Xid errors.

## Uninstall and recovery

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Remove -Apply
```

Nothing else is installed: no files on the internal disks, no boot entry inside
Windows, no driver change.

Black screen or no Windows after a real transaction: hold the power button until
the machine is off, remove the stick, then boot `Windows Boot Manager` from the
firmware boot menu (F7 here). A full power-off restores stock.

## Known limitations

- One machine, one VBIOS (`95.06.15.40.5F`), one vendor. Other AD106M boards must
  pass the survey and get their own exact profile.
- Power and cooling limit the gain: 115 W caps sustained clocks, and the tensor
  path is no longer the bottleneck.
- The unlock is volatile. Sleep, resume, a driver restart or a driver update
  returns the GPU to stock; only a cold boot through the stick restores it.
- Fast Startup must stay off, otherwise a Windows "shut down" skips the firmware
  path and the stick never runs.
- Some laptops bind a boot entry to one USB port; if the entry stops working,
  re-run `-Apply`.
- Firmware that stops with "no boot device" instead of falling back needs the
  entry removed and manual boot-menu selection each time.
- `UNLOCKA2820` is built by default. Use `--safe-only` if you do not want an image
  that unlocks without a key press in the tree.

## Licence and provenance

Code is GPL-2.0-only. Terms and upstream notices: `LICENSE*`,
`THIRD_PARTY_NOTICES.md`, `UPSTREAM-WINDOWS-NOTICES.md`, `NVIDIA-FILES.md`,
`provenance.json`.

Upstream:
- `JustAResearcher/gpu-unlock-ada` — Ada assets, Booter and four-PLM payload
- `MarvinFS/rtx4090-uefi` — Windows UEFI port this repository descends from
- `NekoMirra/rtx4060-laptop-tensor-unlock` — direct base of this port
- `Zagitta/gpu-unlock` — original mechanism
- EDK2 headers, under their own licence

The five files in `assets/` are NVIDIA's signed firmware, downloaded locally under
NVIDIA's own licence and never redistributed here.

Experimental research code, verified on one laptop model, provided without
warranty. It can cause black screens, failed boots, driver faults or data loss.
You are responsible for what you run.
