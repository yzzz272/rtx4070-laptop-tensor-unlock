# RTX 4070 Laptop SURVEY compatibility report

Do **not** run `UNLOCKM2820.EFI` on an unreviewed machine.

## Hardware

- Laptop manufacturer/model:
- BIOS version:
- GPU name:
- PCI ID:
- Subsystem ID:
- BDF:
- VBIOS version:
- VRAM:
- NVIDIA driver:
- Secure Boot state:
- Display driven by dGPU or iGPU:

## Files

Attach the newest `GPU4090-UNLOCK/RUNnnnn.TXT` produced by
`SURVEY2820.EFI`.

Optional, if the owner understands how to capture it safely:

- VBIOS ROM SHA-256:
- Parsed logical ROM-chain SHA-256:
- FWSEC image SHA-256:

## Required log excerpts

```text
GPU at ... subsystem=...
reg PMC_BOOT_0 ...
reg VRAM_MIB ...
gpu_unlock: FWSEC geometry: ...
release preflight: ...
SKIP: ...              # if present
```

## Stock benchmark

Use the same benchmark binary for every comparison and record its SHA-256.

```text
FP16 input / FP16 accumulate:
FP16 input / FP32 accumulate:
BF16 input / FP32 accumulate:
FP16acc / FP32acc ratio:
Benchmark SHA-256:
```
