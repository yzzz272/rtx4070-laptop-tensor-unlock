# RTX 4070 Laptop tensor-rate unlock (Windows UEFI)

**English** | [简体中文](README.zh-CN.md)

A UEFI application that runs before Windows and removes the half-rate limit on
FP16/BF16 tensor operations that accumulate into FP32, on one verified laptop.

It does not flash the VBIOS, patch the driver, modify Windows files, or install a
boot entry. The unlock is volatile: a full power-off restores stock.

> **AI-generated. Verify before use.**
> The code, scripts, tests and this document were written with substantial AI
> assistance. They were built and run on the machine below, but not reviewed by
> a security professional. Read the source before running it, and do not run it
> on a machine you cannot afford to lose.

## Scope

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
subsystem, BDF, VBIOS and firmware behaviour, so their outcome is unknown.

If yours differs, run `SURVEY2820` first. It is read-only: every write, DMA, Bus
Master, PCI write, display release and FLR path is compiled out. It logs your
subsystem, BDF, chip, VRAM and FWSEC geometry, then starts Windows. Open an issue
with that log before trying anything else.

## Measured result

| State | FP16 in / FP16 acc | FP16 in / FP32 acc | Ratio |
|---|---:|---:|---:|
| Stock | 152–158 TF/s | 74–77 TF/s | 2.03–2.13 |
| Unlocked | 152–159 TF/s | 144–160 TF/s | 0.99–1.05 |

The FP16-accumulate control is unchanged; the FP32-accumulate path roughly
doubles. Register readbacks agree: `READOUT_1` goes from `0x410080` to `0`, with
`SS0=0x88888888` and `SS1=0x8` still set after FLR and display reconnect.

Evidence: [`docs/verified-gm5ar7o.md`](docs/verified-gm5ar7o.md),
[`docs/logs/`](docs/logs).

## How it works

1. Read the card's own VBIOS from `BAR0+0x300000` and parse the FWSEC descriptor.
2. Load the signed GSP Falcon firmware to establish WPR2.
3. Run the pinned AD102-family Booter and four-PLM payload on SEC2, opening the
   three permission registers.
4. Write `SS0=0x88888888` and `SS1=0x8`, run one PCIe FLR, verify the selectors
   survived, reconnect the display driver, start Windows.

## Build

Requires Python 3, Zig 0.14.1, and `zstd` on `PATH`.

```powershell
python scripts/make_assets.py --out assets     # NVIDIA inputs, hash-pinned
python build.py --zig C:\path\to\zig.exe --out build
```

`build.py` produces five images. `--safe-only` drops `UNLOCKA2820`, the only one
that unlocks without a key press.

| Image | Writes GPU | Needs a key |
|---|---:|---|
| `SURVEY2820` | no | no |
| `DRYRUN2820` | no | no |
| `RELTEST2820` | no | `U` |
| `UNLOCKM2820` | yes | `U` |
| `UNLOCKA2820` | yes | no |

`python tools/check_reference_build.py` checks your build against the recorded
hashes. This tree reproduces all five byte-for-byte, including both images that
ran on hardware; CI enforces the same check.

## Use

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
# copy stick\ contents to the root of a FAT32 USB drive, then:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply
```

| State | Result |
|---|---|
| Stick plugged in, cold boot | firmware starts the stick, unlocks, Windows starts |
| Stick removed, cold boot | firmware falls back to Windows Boot Manager, GPU stays stock |

Before the first boot: back up your data, turn Secure Boot off, turn Fast Startup
off (`powercfg /h off`), and suspend BitLocker if it is on. Shut down fully, wait
for the power light to go out, hold the power button for 10 seconds, then boot.
The boot menu is F7 on the verified machine.

During the 3-second countdown: `Esc` opens a menu, `S` starts stock Windows, `U`
unlocks immediately. Undo the boot entry with `-Remove -Apply`.

Three things break this, most common first:

- Fast Startup left on: a Windows "shut down" skips the firmware path, so the
  stick never runs.
- The stick moved to another USB port: the recorded device path may not match.
  Re-run `-Apply`.
- Firmware that stops with "no boot device" instead of falling back: delete the
  entry and pick the stick from the boot menu each time.

Sleep, resume, a driver restart or a driver update returns the GPU to stock. Only
a cold boot through the stick restores the unlock.

## Verify a new machine

Do not skip stages.

1. `SURVEY2820` — read-only. Send the log for review.
2. `DRYRUN2820` — exact target only, no writes. Expect `Checks passed.`
3. `RELTEST2820` — press `U`. Expect `release test: status=0 gop=1`.
4. `UNLOCKM2820` — press `U`. Expect `TRANSACTION OK`.

```powershell
python scripts/make_stick.py --layout staged --out stick
```

## If it fails

Stop at the first failed stage. Before any write, a failure logs the reason and
starts stock Windows. After a write, the application contains the card and stops.

If the screen says `STOPPED`, or Windows has not started after about two minutes:
hold the power button until the machine is off, remove the stick, boot Windows
Boot Manager. A full power-off restores stock.

## Repository

```text
target_2820.h                  exact write target
build.py                       build (--safe-only drops the auto image)
scripts/make_assets.py         firmware assets from pinned NVIDIA inputs
scripts/make_stick.py          plug-and-unlock or staged USB layout
scripts/usb_boot_entry.ps1     reversible firmware boot entry
tools/check_reference_build.py build vs recorded hashes
vendor/, compat/               transaction core and UEFI compatibility layer
tests/                         simulated PCI/MMIO/DMA/failure suites
docs/                          report, logs, reference hashes
```

## Licence and provenance

GPL-2.0-only. Terms and upstream notices: `LICENSE*`, `THIRD_PARTY_NOTICES.md`,
`NVIDIA-FILES.md`, `provenance.json`. Built on `JustAResearcher/gpu-unlock-ada`,
`MarvinFS/rtx4090-uefi`, `NekoMirra/rtx4060-laptop-tensor-unlock` and
`Zagitta/gpu-unlock`. NVIDIA firmware is downloaded locally and never
redistributed here.

## Disclaimer

Experimental research code, verified on one laptop model, provided without
warranty. It can cause black screens, failed boots, driver faults or data loss.
You are responsible for what you run.
