# Security policy

## What this project does

`rtx4070-laptop-tensor-unlock` is an experimental UEFI application that runs
before Windows and, on one exact laptop configuration, changes volatile GPU
registers and performs a PCIe Function Level Reset. It does not flash the VBIOS,
does not modify Windows files, and does not install a boot entry.

## Reporting a problem

Open a GitHub issue for anything that is not a security-sensitive report.

Report privately, through GitHub's "Report a vulnerability" advisory flow, if
you find:

- a way to make a write-capable image act on a GPU other than the pinned target;
- a way to make `SURVEY2820` perform a GPU write, DMA, Bus Master enable, PCI
  config write, display release or FLR;
- a path that leaves DMA buffers or Bus Master enabled after a failed
  transaction;
- a way to bypass the manual `U` confirmation in `UNLOCKM2820`;
- a supply-chain problem in the firmware generators or the build.

Please include the build hash from `build/build-result.json`, the affected
image, and the relevant `RUNnnnn.TXT` log.

## Scope

In scope:

- `app.c`, `boot_io.c`, `release.c`, `port.c`, `checks.c`, `profile.c`
- `vendor/` (the retained transaction core)
- `scripts/`, `firmware/`, `tools/`, `build.py`
- the CI workflow

Out of scope:

- NVIDIA's firmware files themselves (report those to NVIDIA);
- upstream projects, which have their own policies;
- hardware damage caused by running an image on a machine it was not verified
  on — that is documented as unsupported.

## Safety expectations

Every write-capable image must refuse, before the first GPU write, when any of
these differ from the pinned profile: PCI ID, subsystem ID, BDF, or FWSEC
geometry. A refusal must end in stock Windows, not in a retry.

## Supported versions

Only the latest tagged release is supported. This is research code: there is no
guarantee of a fix, and no guarantee that any given laptop will work.
