# Firmware assets are generated locally

This source-only repository does not redistribute NVIDIA firmware binaries.
Generate the five required files from NVIDIA's published packages:

```powershell
python scripts/make_assets.py --out assets
```

The generator downloads pinned inputs, verifies their SHA-256 values from
`firmware/artifacts-610.43.03.json`, and writes:

- `booter_load_ad102.bin`
- `v67-ad102-610.43.03-four-plm.bin`
- `gsp_ga10x.bin`
- `gsp_boot_ad102.bin`
- `gsp_boot_desc_ad102.bin`
- `NVIDIA-LICENSE`

A `zstd` executable must be available on `PATH`.
