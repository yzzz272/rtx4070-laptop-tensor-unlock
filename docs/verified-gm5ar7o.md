# RTX 4070 Laptop `10de:2820` local canary report

## Machine

- Laptop: MECHREVO JiguangPro Series GM5AR7O
- GPU: NVIDIA GeForce RTX 4070 Laptop GPU (AD106M), 36 SM
- PCI: `10de:2820`, subsystem `1d05:1297`, BDF `0000:01:00.0`
- VBIOS: `95.06.15.40.5F`
- VRAM: 8188 MiB
- Default power limit: 115 W
- NVIDIA driver: 617.42
- Current OS: Windows 10 Pro N for Workstations 19045
- Secure Boot: enabled
- NVIDIA GPU is display-active; no integrated display adapter was visible in Windows inventory.

## Stock tensor-rate probe

A read-only CUDA WMMA probe was built locally with CUDA 13.4 for `sm_89`. It only
allocates CUDA memory and dispatches kernels; it performs no PCI/MMIO/firmware writes.

Three representative runs:

| Mode | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| FP16 input / FP16 accumulate | 152.24 | 157.94 | 155.68 TF/s |
| FP16 input / FP32 accumulate | 74.13 | 74.31 | 76.67 TF/s |
| FP16-acc / FP32-acc ratio | 2.054 | 2.126 | 2.030 |

The stable ratio near 2.0 is the consumer Ada half-rate signature. A successful
unlock should move this ratio toward 1.0, though absolute application gains will
be limited by the laptop's 115 W power budget.

## VBIOS capture and offline parsing

GPU-Z 2.71.0 was downloaded from TechPowerUp and verified against the publisher's
SHA-256 before use:

`A2412D6720E091F65925622561C3F274A25ECD0B9FB0F50AB3B910918F01DEE9`

GPU-Z paused the display driver and saved a 2,048,000-byte ROM container.

- Saved ROM SHA-256: `190e53ab319978c2332dc8d295b290514fe64855a01aa2e7d62e0614539c51ed`
- The container holds two identical complete option-ROM chains at `0x9400` and
  `0xe9400`.
- Logical chain length: `0xa2a00` bytes
- Logical chain SHA-256: `892452e95395d677ddbd714a999a559a6b3f2b42f2869bbf32afe142de10eb95`
- PCI identity parsed from both chains: `10de:2820`

The unmodified bounded parser from `JustAResearcher/gpu-unlock-ada` accepted both
chains and returned:

```text
FWSEC descriptor: offset=0x4655c
FWSEC image_off=0x46888
FWSEC image_size=0x10300
IMEM size=0xf500
DMEM size=0xd80
IMEM/DMEM physical addresses=0
PKC offset=0xb24
interface offset=0x1c
engine mask=0x400
ucode id=9
signature count=2
signature versions=0x3
signature bytes=768
```

FWSEC image SHA-256:
`a32b8838a4e8d72fbfd2b8808c5ce5c9a36f52a72f2f273379b70c97c02269c0`

The size/IMEM/DMEM/signature geometry matches a demonstrated successful AD104
Windows transaction (`0x10300 / 0xf500 / 0xd80 / 2 signatures`). The board-specific
image offset differs, as expected. This is positive compatibility evidence, not
proof that a write transaction or driver handoff will succeed on this laptop.

## Local Linux canary patch

`ad106m-2820-canary.patch` adds `10de:2820` behind the existing
`ad106_experimental` opt-in, exact BDF only, and routes it through the pinned AD10x
assets. It also updates mocked dispatch and boot-option tests.

Expected Linux boot options:

```text
gpu_unlock.targets=0000:01:00.0 gpu_unlock.ad106_experimental=1 nvidia.NVreg_DynamicPowerManagement=0x00
```

The Python boot-option tests pass. Full C/Linux module tests cannot run in the
current Windows-only environment because no Linux compiler/make environment or
bare-metal Linux installation is present.

## Windows UEFI canary result

A machine-specific Windows UEFI canary was built from the guarded RTX 4060
Laptop port and pinned to `10de:2820`, subsystem `1d05:1297`, BDF
`0000:01:00.0`, and the exact FWSEC geometry above. Testing progressed through
read-only DRYRUN, display release/reconnect RELTEST, and a manual real
transaction from a FAT32 USB drive.

The real transaction completed successfully on 2026-10-28:

- Chip readout: `PMC_BOOT_0=0x196000a1`
- Required permissions opened by the signed firmware payload
- `SS0=0x88888888`, `SS1=0x8`
- Speed readout changed from `0x410080` to `0`
- PCIe FLR returned success
- Selectors and full-rate readout survived FLR and GOP reconnect
- DMA was fully released and PCI configuration restored
- NVIDIA Windows driver 617.42 loaded normally at `00000000:01:00.0`
- No relevant `nvlddmkm`, Display, NVIDIA, or Xid system events were found

Transaction log:

- `windows-unlock-RUN0006.txt`
- SHA-256: `427992bb5bd1aa1fe5fc4eaa7c1d4790ab9ffeef8c0c467a1306a53f699a51c`

Matched CUDA probe results changed from the stock ratios `2.054`, `2.126`, and
`2.030` to unlocked ratios near one. Two three-run unlocked sets produced:

- First set: `0.995`, `0.994`, `1.009`
- Recorded set: `0.996`, `0.989`, `1.054`

FP16-input/FP32-accumulate throughput rose from roughly `74-77 TF/s` stock to
roughly `144-160 TF/s` unlocked, while FP16-accumulate remained in the same
roughly `152-159 TF/s` range. This is a matched confirmation that the tensor
half-rate restriction was removed on this exact RTX 4070 Laptop GPU.

Recorded probe output:

- `windows-unlocked-tensor-probe.txt`
- SHA-256: `8f4e54186eda0801f125c5462aedaae0183265d6116fcac7bac27700c2bacfa9`

## Current operational status

The unlock is volatile and is lost after a full power-off. The USB currently
uses the manual `UNLOCKM` image, so a cold boot must select the USB and capture
`U` to unlock. The original `TOTORONG/AD103_win_unlocker` remains incompatible
and must not be run. Automatic USB or internal-ESP startup should only be
considered after additional cold-boot and workload stability testing.
