# Changelog

## 0.2.0 — plug and unlock

- `UNLOCKA2820` is now part of the default build; `--safe-only` drops it.
- `scripts/make_stick.py` defaults to a single plug-and-unlock layout: the root
  image is the automatic one, the other four images sit in `RECOVERY/`.
  `--layout staged` keeps the previous per-stage directories.
- Added `scripts/usb_boot_entry.ps1`, which registers the stick ahead of Windows
  Boot Manager so a plugged-in stick unlocks and a removed stick falls back to
  Windows. Dry run by default, `-Apply` to act, `-Remove -Apply` to undo, with
  an install record under `%ProgramData%\Rtx4070Unlock`.
- Documented the fallback caveats: Fast Startup must be off, some laptops bind a
  device path to one USB port, and the fallback has to be verified by hand.
- No firmware image changed; every recorded hash still reproduces.

## 0.1.0 — verified AD106M Windows UEFI canary

- Ported the guarded Windows UEFI flow to RTX 4070 Laptop GPU `10de:2820`.
- Added the exact verified target profile in `target_2820.h`:
  - subsystem `1d05:1297`
  - BDF `0000:01:00.0`
  - VBIOS/FWSEC geometry from `95.06.15.40.5F`
- Routed AD106M through the pinned Ada Booter/GSP/four-PLM asset family.
- Added `SURVEY2820.EFI`, a read-only inventory build that accepts any single
  `10de:2820` while keeping all GPU writes, DMA, Bus Master, PCI writes, display
  release and FLR disabled.
- Renamed build outputs to `SURVEY2820`, `DRYRUN2820`, `RELTEST2820` and
  `UNLOCKM2820`.
- Removed the automatic real-unlock build and internal-ESP installation package
  from this source-only distribution.
- Added `UNLOCKA2820.EFI`, built only with `--with-auto`: the same transaction,
  started automatically after the countdown, still cancellable with Esc/S.
- Made the published tree reproduce the hardware-verified images byte-for-byte:
  `docs/reference-build-result.json` records them and
  `tools/check_reference_build.py` (also run by CI) enforces the match.
- Added exact FWSEC profile constants and a survey-specific bounds-only parser
  gate.
- Added survey admission tests while retaining transaction, app-flow and display
  release simulation suites.
- Verified a real Windows transaction on MECHREVO GM5AR7O:
  - selectors survived FLR and GOP reconnect
  - NVIDIA driver 617.42 initialized normally
  - FP16-input/FP32-accumulate throughput rose from about 74–77 TF/s to
    144–160 TF/s
  - matched rate ratio changed from about 2.0 to about 1.0
