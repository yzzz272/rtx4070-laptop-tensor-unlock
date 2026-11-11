# RTX 4070 Laptop tensor-rate unlock (Windows UEFI)

**English** | [简体中文](README.zh-CN.md)

> ## ⚠️ AI-generated project — verify before you use it
>
> This repository — the code, the build scripts, the tests and this document —
> was produced with substantial AI assistance. It has been built and tested on
> the one machine described below, but it has **not** been reviewed by a
> security professional, and AI-generated systems code can be wrong in ways
> that are hard to see.
>
> Read the source before running any image. Do not run it on a machine you
> cannot afford to lose. Do not trust the benchmark numbers here as a promise
> about your own hardware. If you cannot read C and UEFI code well enough to
> judge it, ask someone who can.

A pre-boot UEFI application that removes the half-rate restriction on FP16/BF16
Tensor Core operations that accumulate into FP32, on consumer Ada laptop GPUs.

- Does **not** flash the VBIOS
- Does **not** replace or patch the NVIDIA Windows driver
- Does **not** modify Windows system files
- Does **not** install a boot entry or touch the internal ESP
- The unlock is **volatile**: a full power-off returns the GPU to stock

This is not a power-limit, VRAM or gaming unlock. It only helps workloads that
feed FP16/BF16/TF32 data into tensor cores and accumulate in FP32.

---

## Verification scope — read this first

Exactly **one** machine has been verified end to end:

| Item | Value |
|---|---|
| Laptop | MECHREVO JiguangPro Series **GM5AR7O** |
| GPU | RTX 4070 Laptop GPU, AD106M, 36 SM |
| PCI ID | `10de:2820` |
| Subsystem | `1d05:1297` |
| BDF | `0000:01:00.0` |
| VBIOS | `95.06.15.40.5F` |
| Chip readout | `PMC_BOOT_0=0x196000a1` |
| NVIDIA driver | 617.42 |
| Windows | 10 Pro N for Workstations 19045 |

**Every other RTX 4070 Laptop is unverified.** Different brands, subsystems,
BDFs, VBIOS revisions and EC/firmware behaviour all change the outcome. A
result on this machine says nothing about yours.

If your laptop is not the table above, the only supported first step is the
read-only `SURVEY2820` image:

1. Build `SURVEY2820.EFI` and boot it from a USB drive.
2. It records your subsystem, BDF, chip readout, VRAM and FWSEC geometry, then
   starts Windows normally.
3. It cannot write the GPU: every write, DMA, Bus Master, PCI config write,
   display-release and FLR gate is compiled out.
4. Open an issue with the report from
   [`docs/compatibility-report-template.md`](docs/compatibility-report-template.md).

A new machine gets its own exact target profile only after that log has been
reviewed. Editing the constants yourself and skipping this step is how people
brick laptops.

---

## Measured result on the verified machine

Same machine, same CUDA probe binary, same shapes:

| State | FP16 in / FP16 acc | FP16 in / FP32 acc | Ratio |
|---|---:|---:|---:|
| Stock | ~152–158 TF/s | ~74–77 TF/s | `2.030–2.126` |
| Unlocked | ~152–159 TF/s | ~144–160 TF/s | `0.989–1.054` |

The FP16-accumulate control group barely moves; the FP32-accumulate path
roughly doubles. Hardware readbacks agree:

```text
before:     READOUT_1=0x410080  full=0
selectors:  SS0=0x88888888  SS1=0x8
post-FLR:   READOUT_1=0  full=1
POST-GOP:   SS0=0x88888888  SS1=0x8
TRANSACTION OK
```

Evidence in the repository:

- [`docs/verified-gm5ar7o.md`](docs/verified-gm5ar7o.md)
- [`docs/logs/RUN0006-success.txt`](docs/logs/RUN0006-success.txt) — manual image
- [`docs/logs/RUN0001-auto-success.txt`](docs/logs/RUN0001-auto-success.txt) — automatic image
- [`docs/logs/unlocked-tensor-probe.txt`](docs/logs/unlocked-tensor-probe.txt)

These numbers are one laptop with one thermal design. Expect throttling, not a
free 2× in every application.

---

## How it works, briefly

Consumer Ada parts run the FP32-accumulate tensor path at half the FP16-accumulate
rate. The restriction is set by two volatile speed selectors (`SS0`, `SS1`) and
four PLM permission registers, and only NVIDIA's own signed firmware chain can
open them.

Before Windows starts, the application:

1. Reads the card's own VBIOS from `BAR0+0x300000` and parses the FWSEC
   descriptor.
2. Loads the signed GSP Falcon firmware to establish WPR2.
3. Runs the pinned AD102-family Booter and four-PLM payload on SEC2, opening
   `WPR_CFG`, `WPR` and `FEAT_OVR_PLM`.
4. Writes `SS0=0x88888888` and `SS1=0x8`, then reads them back.
5. Performs one PCIe Function Level Reset and verifies the selectors survived.
6. Reconnects the firmware display driver and hands control to the existing
   Windows Boot Manager.

Because the selectors are volatile, this runs again on every cold boot.

---

## Build modes

`build.py` produces all five images by default. `--safe-only` leaves out
`UNLOCKA2820`, the only image that unlocks without a key press.

| Image | Admitted target | GPU writes | Display release | Key press |
|---|---|---:|---:|---|
| `SURVEY2820.EFI` | any single `10de:2820` | no | no | none |
| `DRYRUN2820.EFI` | exact profile | no | no | none |
| `RELTEST2820.EFI` | exact profile | no | yes | `U` |
| `UNLOCKM2820.EFI` | exact profile | **yes** | yes | **`U`** |
| `UNLOCKA2820.EFI` | exact profile | **yes** | yes | none (3 s) |

The exact profile means PCI ID, subsystem, BDF and FWSEC geometry must all match
[`target_2820.h`](target_2820.h). Any mismatch is refused before the first write.

`UNLOCKA2820` is the plug-and-unlock image: it is what the default USB layout
puts at the root. During its countdown, `Esc` opens a two-entry menu and `S`
starts stock Windows.

---

## Requirements

- Python 3
- Zig **0.14.1**
- `zstd` on `PATH` (only to generate firmware assets)
- Network access for the pinned NVIDIA inputs

```powershell
winget install Facebook.Zstandard
```

Zig does not need to be installed system-wide; pass the executable path.

---

## Build

### 1. Generate the firmware assets

NVIDIA's binaries are not redistributed here.

```powershell
python scripts/make_assets.py --out assets
```

This downloads pinned inputs, verifies their SHA-256 values and writes five
files plus the NVIDIA licence into `assets/`.

### 2. Build the images

```powershell
python build.py --zig C:\path\to\zig.exe --out build
# four images only, no automatic unlock
python build.py --zig C:\path\to\zig.exe --out build --safe-only
```

Output goes to `build/` with `build/build-result.json`. Images are PE-checked
and built with `/Brepro`, so the same source and Zig version produce identical
bytes.

### 3. Reproducibility check

```powershell
python tools/check_reference_build.py
```

This compares your build with
[`docs/reference-build-result.json`](docs/reference-build-result.json). The
current tree reproduces all five recorded images byte-for-byte, including both
images that were run on hardware:

| Image | SHA-256 (first 16) |
|---|---|
| `SURVEY2820.EFI` | `bb4c3368402d52f0` |
| `DRYRUN2820.EFI` | `cf98446deb858daa` |
| `RELTEST2820.EFI` | `0d640e93a585c03e` |
| `UNLOCKM2820.EFI` | `2929454ea73fe85b` |
| `UNLOCKA2820.EFI` | `58085a8d9f9dce0d` |

CI runs the same comparison, so any change that alters the output is called out.

---

## Tests

All tests are simulated: PCI, MMIO, DMA, firmware execution and failure paths
run against a fake engine. Nothing touches a real GPU.

```sh
export CC='C:/path/to/zig.exe cc'

sh tests/run-survey-tests.sh
sh tests/make_placeholder_assets.sh /tmp/assets
sh tests/run-boot-app-tests.sh /tmp/assets
sh tests/run-release-tests.sh
```

The full transaction simulation additionally needs a 1 MiB PROM window from the
target card and the real firmware assets:

```sh
sh tests/run-host-tests.sh /path/to/PROM-1MiB.bin assets
```

Neither input is published, so that suite stays local. CI runs the other three.

---

## Preparing the USB drive

> This erases the USB drive. Confirm the disk number, model and size before you
> run anything destructive. Never select a system disk.

```powershell
# plug-and-unlock layout (default): the root image unlocks automatically
python scripts/make_stick.py --build build --assets assets --out stick

# one directory per stage, for first-time verification on a new machine
python scripts/make_stick.py --build build --assets assets --out stick --layout staged
```

The default layout is a single stick:

```text
EFI/BOOT/BOOTX64.EFI     <- UNLOCKA2820, automatic
GPU4090-ASSETS/...
RECOVERY/                <- the other four images
README-AUTO.txt
SHA256SUMS
```

The staged layout produces one directory per stage, each containing:

```text
EFI/BOOT/BOOTX64.EFI
GPU4090-ASSETS/...
SHA256SUMS
```

Copy the **contents** of one directory to the root of a FAT32 USB drive. Only one
`EFI/BOOT/BOOTX64.EFI` can exist at a time.

`GPU4090-ASSETS` and `GPU4090-UNLOCK` are legacy upstream path names. They are
kept because renaming them would change the bytes of the images that were
verified on hardware.

---

## Staged procedure

Do not skip stages. Each one exists to stop a failure before it reaches the GPU.

### Before every boot

1. Back up anything important.
2. If BitLocker or device encryption is on, back up the recovery key and
   suspend protection.
3. Turn Secure Boot **off**; the images are unsigned.
4. Turn Windows Fast Startup **off**.
5. Connect the power adapter.
6. Fully shut down Windows.
7. Wait for the power light to go out, then hold the power button for about
   10 seconds.
8. Power on, open the firmware boot menu (F7 on the verified machine), and pick
   the entry with `UEFI` in its name.

Do not use Windows "Restart" instead of a cold boot. A GPU that the driver has
already initialised is rejected by the cold-entry check.

Some laptops never draw the text console. If a stage needs a key press, select
the USB entry and press the key repeatedly for a few seconds right after Enter.

### Stage A — `SURVEY2820` (any 4070 Laptop)

No key press. It records hardware facts and starts Windows. Send the resulting
`\GPU4090-UNLOCK\RUNnnnn.TXT` back for review.

### Stage B — `DRYRUN2820` (exact profile only)

No key press, no display release, no GPU write. A good log contains:

```text
PCI scan: 10de:2820 functions found=1
PCIe device capability=... FLR_capable=1
FWSEC from this card's VBIOS: image_off=... image_size=...
release preflight: status=0
Checks passed.
```

### Stage C — `RELTEST2820`

Press `U` during the countdown. The screen may freeze or go blank. A good log
contains:

```text
choice: unlock
driver release: status=0 refresh=0 same_pci=1
release test: status=0 gop=1
```

Still no GPU write.

### Stage D — `UNLOCKM2820` (real transaction)

Only after B and C pass. Press `U`. A good log contains:

```text
selector result: SS0=0x88888888 ... matched=1
selector result: SS1=0x8 ... matched=1
AD102 selectors-applied: readout1=0 ... full=1
PCIe FLR returned: result=0
AD102 post-FLR: readout1=0 ... full=1
POST-GOP SS0=0x88888888 SS1=0x8
TRANSACTION OK
```

Then stay in Windows and measure before rebooting.

---

## Checking the result

Do not judge by absolute TFLOPS alone; clocks and power limits move. Compare
the ratio of FP16-accumulate to FP32-accumulate throughput from the same binary:

- stock: about `2.0`
- unlocked: about `1.0`

Also check:

```powershell
nvidia-smi
```

and look for `nvlddmkm`, `Display` or Xid errors in the Windows system log.

---

## Stop conditions and recovery

Stop and do not continue to the next stage if any of these happen:

- PCI ID, subsystem, BDF or FWSEC geometry differs from the target profile
- FLR is not supported
- `release preflight` fails
- the display driver cannot be restored
- any selector, permission, FLR or POST-GOP readback does not match
- Windows reports a device error, Xid, corruption or a persistent black screen

If the screen shows `STOPPED. Power OFF with the power button.`, or the machine
does not reach Windows within about two minutes after a real transaction:

1. Hold the power button until the machine is fully off.
2. Remove the USB drive.
3. Boot the original Windows Boot Manager.

All changes are volatile; a full power-off returns the card to stock.

The unlock is also lost after sleep/resume, a driver restart, or a driver
update. Reboot with the USB to unlock again.

---

## Plug and unlock

The default USB layout is built for one behaviour:

| State | What happens |
|---|---|
| stick plugged in, cold boot | firmware starts the stick, the image unlocks, Windows starts |
| stick removed, cold boot | firmware falls back to Windows Boot Manager, GPU stays stock |

For the firmware to try the stick first, either put it ahead of Windows Boot
Manager in the firmware setup, or register a boot entry once:

```powershell
# dry run: shows what would change
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1

# create the entry and put it first
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply

# undo
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Remove -Apply
```

The script refuses to act unless the volume is a removable FAT32 volume with the
expected label, the root image is the released automatic image (SHA-256 checked),
Secure Boot is off, and no entry is already recorded. It records the entry id in
`%ProgramData%\Rtx4070Unlock\usb-entry.json` so `-Remove` can undo it exactly.

Things that break the fallback, check them before relying on it:

- **Fast Startup must be off.** With it on, a Windows "shut down" can skip the
  firmware boot path entirely, so the stick never runs. `powercfg /h off`.
- **The USB port matters on some laptops.** A device path recorded for one port
  may not match another; if the entry stops working, re-run `-Apply`.
- **Verify the fallback yourself.** Shut down, remove the stick, power on, and
  confirm Windows starts. If your firmware stops with "no boot device" instead
  of falling back, delete the entry and select the stick from the boot menu
  (F7) each time instead.
- **Sleep and resume, driver restarts and driver updates** return the GPU to
  stock. Only a cold boot through the stick restores the unlock.

Automation does not make the unlock permanent: the selectors are volatile and a
full power-off clears them. The stick simply repeats the transaction on every
cold boot.

---

## Repository layout

```text
target_2820.h                  exact write target
build.py                       reproducible build (--safe-only drops the auto image)
tools/check_reference_build.py verifies the build against recorded hashes
scripts/make_assets.py         generates firmware assets from pinned NVIDIA inputs
scripts/make_stick.py          builds the plug-and-unlock or staged USB layout
scripts/usb_boot_entry.ps1     adds/removes the firmware boot entry for the stick
firmware/                      download, verify and generation scripts
vendor/                        retained transaction core and EDK2 headers
compat/                        UEFI compatibility layer
tests/                         simulated PCI/MMIO/DMA/failure suites
docs/                          hardware report, logs, reference hashes
```

---

## Provenance and licensing

Code is GPL-2.0-only. Upstream projects and their licences are recorded in
`LICENSE*`, `THIRD_PARTY_NOTICES.md`, `UPSTREAM-WINDOWS-NOTICES.md`,
`NVIDIA-FILES.md` and `provenance.json`.

Upstream work this repository builds on:

- `JustAResearcher/gpu-unlock-ada`
- `MarvinFS/rtx4090-uefi`
- `NekoMirra/rtx4060-laptop-tensor-unlock`
- `Zagitta/gpu-unlock`
- EDK2 headers, under their own licence
- NVIDIA firmware inputs, under NVIDIA's own licence, downloaded locally and
  never redistributed here

---

## Disclaimer

Experimental hardware research code, written with AI assistance and verified on
a single laptop model. It can cause black screens, failed boots, driver faults
or data loss. Results on one machine do not transfer to another. Do not delete
the exact-target checks to "make it work". You must be able to cut power, reach
the firmware boot menu, and boot the original Windows entry.

No warranty of any kind. You are responsible for what you run.
