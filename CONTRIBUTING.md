# Contributing

Thanks for looking at this project. It is a small, deliberately conservative
code base: a UEFI application that runs before Windows and touches GPU
registers exactly once.

## Ground rules

1. **Never widen admission to make an untested card "work".** The write-capable
   builds pin PCI ID, subsystem, BDF and FWSEC geometry. Removing a check is not
   a contribution.
2. **Keep the survey build read-only.** `GU_2820_SURVEY` must leave every GPU
   write, DMA, Bus Master, PCI config write, display release and FLR gate closed.
3. **Do not commit firmware binaries.** `assets/` is generated locally by
   `scripts/make_assets.py`; NVIDIA's files are not redistributed here.
4. **Do not add an installer that edits the internal ESP or the firmware boot
   order.** The project intentionally ships images and documentation only.
5. **Keep the reference build reproducible.** `docs/reference-build-result.json`
   records the images verified on hardware. If your change alters any of them,
   say so explicitly in the pull request and explain why the change is needed.

## Before opening a pull request

```sh
python build.py --out build --with-auto
python tools/check_reference_build.py     # must reproduce the recorded images

CC="zig cc" sh tests/run-survey-tests.sh
sh tests/make_placeholder_assets.sh /tmp/assets
CC="zig cc" sh tests/run-boot-app-tests.sh /tmp/assets
CC="zig cc" sh tests/run-release-tests.sh
```

The full transaction simulation needs a 1 MiB PROM dump from the target card and
the real firmware assets:

```sh
CC="zig cc" sh tests/run-host-tests.sh /path/to/PROM-1MiB.bin assets
```

CI runs the build, the reference comparison, the survey, boot/app and release
suites. It cannot run `run-host-tests.sh` because neither input is published.

## Reporting a new laptop

Do not send a pull request that flips constants for your machine. Instead:

1. Build `SURVEY2820.EFI` and run it on the laptop.
2. Fill in `docs/compatibility-report-template.md` from the new
   `GPU4090-UNLOCK/RUNnnnn.TXT`.
3. Open an issue with that report.

A new machine gets its own exact target profile only after the survey log has
been reviewed, and only with its own subsystem, BDF and FWSEC geometry.

## Style

- C sources are C11, freestanding, `-Wall -Wextra -Werror`.
- Keep the existing brace and spacing style of the file you touch.
- Comments explain *why* a check exists, not what the line does.
- Python: standard library only, no new dependencies.
- Commits: one logical change, imperative subject line.

## Licence

Contributions are accepted under GPL-2.0-only, matching `LICENSE`.
