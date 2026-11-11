/* SPDX-License-Identifier: GPL-2.0-only */
/* RTX 4070 Laptop (AD106M, 10de:2820) canary admission: exact PCI/subsystem/BDF,
 * the five firmware files with their exact sizes, the exact known FWSEC geometry parsed
 * from this card's VBIOS, and the Linux module's GFW / PLM / WPR2 cold-state gate.
 * The firmware files are NOT hash-checked: the hardware authenticates the signed NVIDIA
 * images itself, the payload only runs in the volatile transaction, and a wrong or damaged
 * file ends in a failed attempt and a power cycle. Hashes of the small files are logged. */
#include "profile.h"
#include "checks.h"
#include "sha256.h"
#include "compat/compat.h"

static const struct {
  const char *name,*hash; /* hash: reference value, logged only (diagnosis), never enforced */
  UINTN bytes;
} Pins[5]={
 {"gpu-unlock/610.43.03/booter_load_ad102.bin","6ee05b20e1dc244c08c052f36ef28469b8d09f4955d1fe33e48a179e11a7fd49",57672},
 {"gpu-unlock/610.43.03/v67-ad102-610.43.03-four-plm.bin","44c36b2d6b3424e53e18f3e55db85c833655de071ce66ce42749588a4a7dc8cb",64000},
 {"gpu-unlock/610.43.03/gsp_ga10x.bin",NULL,84277400}, /* 84 MB, not hashed at boot */
 {"gpu-unlock/610.43.03/gsp_boot_ad102.bin","45d6335a8185d6ff13e8d1484cea73f68d3d13aa1c19dc080ed1c3482dd5bac0",36864},
 {"gpu-unlock/610.43.03/gsp_boot_desc_ad102.bin","83f8f3f1f5f9496e0ea8fc7103c2beb64d0b6de2f5ffe725f13514de5a95fa42",84}
};
BOOLEAN GuAd104AssetsValid(VOID) {
  for(UINTN i=0;i<5;i++)
    if(!GuAssets[i].name || strcmp(GuAssets[i].name,Pins[i].name) ||
       GuAssets[i].firmware.size!=Pins[i].bytes || !GuAssets[i].firmware.data)return FALSE;
  return TRUE;
}
/* Record what was loaded, so a failed attempt can be matched against a known-good set. */
static VOID LogAssets(VOID) {
  static const char digits[]="0123456789abcdef";
  for(UINTN i=0;i<5;i++) {
    char hex[65];UINT8 d[32];
    if(!Pins[i].hash){GuLog("asset %s bytes=%zu (not hashed)\n",Pins[i].name,(size_t)Pins[i].bytes);continue;}
    GuSha256(GuAssets[i].firmware.data,Pins[i].bytes,d);
    for(UINTN j=0;j<32;j++){hex[2*j]=digits[d[j]>>4];hex[2*j+1]=digits[d[j]&15];}hex[64]=0;
    GuLog("asset %s bytes=%zu sha256=%s reference=%s\n",Pins[i].name,(size_t)Pins[i].bytes,hex,
      !memcmp(hex,Pins[i].hash,64)?"match":"DIFFERS");
  }
}
/* SURVEY records any parser-accepted geometry while all write gates are closed.
 * Every other build enforces the exact profile from target_2820.h. */
BOOLEAN GuAd104FwsecSane(const struct gpu_unlock_fwsec *f) {
#if defined(GU_2820_SURVEY)
  return f && f->image_size && f->image_size<=0x100000 && f->image_off<1048576 &&
    f->image_size<=1048576-f->image_off && f->imem_size && f->dmem_size &&
    f->sig_count && f->sig_bytes;
#else
  return f && f->image_off==GU_FWSEC_IMAGE_OFF && f->image_size==GU_FWSEC_IMAGE_SIZE &&
    f->imem_pa==GU_FWSEC_IMEM_PA && f->imem_size==GU_FWSEC_IMEM_SIZE && f->imem_va==GU_FWSEC_IMEM_VA &&
    f->dmem_pa==GU_FWSEC_DMEM_PA && f->dmem_size==GU_FWSEC_DMEM_SIZE && f->pkc_off==GU_FWSEC_PKC_OFF &&
    f->interface_off==GU_FWSEC_INTERFACE_OFF && f->ucode_id==GU_FWSEC_UCODE_ID &&
    f->engine_mask==GU_FWSEC_ENGINE_MASK && f->sig_count==GU_FWSEC_SIG_COUNT &&
    f->sig_versions==GU_FWSEC_SIG_VERSIONS && f->sig_bytes==GU_FWSEC_SIG_BYTES;
#endif
}

/* The slot and BAR0 come from discovery; here the card must still be the same card there. */
static BOOLEAN Config(VOID) {
  UINT32 c[64];UINTN s,b,d,f;GU_CAPS caps;
  if(!Gu.pci || !Gu.located || !Gu.pci->GetLocation || !Gu.pci->Pci.Read || Gu.bar_size!=GU_BAR0_BYTES ||
     EFI_ERROR(Gu.pci->GetLocation(Gu.pci,&s,&b,&d,&f)) ||
     s!=Gu.seg || b!=Gu.bus || d!=Gu.dev || f!=Gu.fun)return FALSE;
  for(UINTN i=0;i<64;i++)
    if(EFI_ERROR(GuConfigRead(EfiPciIoWidthUint32,(UINT32)i*4,&c[i])))return FALSE;
  if(!GuCheckConfig(c,s,b,d,f,&caps) || c[4]!=(UINT32)Gu.bar_base)return FALSE;
  return caps.pm==Gu.pm_cap && caps.pcie==Gu.pcie_cap &&
    caps.pcie_version==Gu.pcie_version && caps.msi==Gu.msi_cap && caps.msix==Gu.msix_cap;
}
VOID GuProfileLogRegisters(VOID) {
  static const struct {UINT32 offset;const char *name;} regs[]={
    {0,"PMC_BOOT_0"},{0x118128,"GFW_PLM"},{0x118234,"GFW_BOOT"},{0x110100,"GFW_CPUCTL"},
    {0x1fa824,"WPR2_LO"},{0x1fa828,"WPR2_HI"},{0x823804,"FEAT_OVR_PLM"},{0x823814,"READOUT_0"},
    {0x823818,"READOUT_1"},{0x82381c,"SS0"},{0x823820,"SS1"},{0x1183a4,"VRAM_MIB"}};
  for(UINTN i=0;i<sizeof(regs)/sizeof(regs[0]);i++)
    GuLog("reg %s %#x = %#x\n",regs[i].name,regs[i].offset,GuRead32(regs[i].offset));
}
static BOOLEAN Usable(UINT32 v){return v!=0xffffffff && (v&0xffff0000)!=0xbadf0000;}
/* Selectors and the feature PLM must be readable and not already open (the Linux module's
 * EALREADY gate), and WPR2 must be down (its EBUSY gate). The GFW assessment itself runs
 * in the retained core. */
static BOOLEAN Registers(UINT32 *Ss0,UINT32 *Ss1) {
  UINT32 chip=GuRead32(0),plm=GuRead32(0x823804),hi=GuRead32(0x1fa828);
  *Ss0=GuRead32(0x82381c);*Ss1=GuRead32(0x823820);
  return !Gu.fault && Usable(chip) && Usable(plm) && plm!=0xffffffff && !(hi>>4) &&
    Usable(*Ss0) && Usable(*Ss1) && *Ss0!=0x88888888 && *Ss1!=0x8;
}
BOOLEAN GuAd104ColdEntry(VOID) {
  UINT32 ss0,ss1;
  return !Gu.started && !Gu.fault && !Gu.retained && Config() &&
    Registers(&ss0,&ss1) && GuEntrySelectorsMatch(ss0,ss1);
}
EFI_STATUS GuAd104Prepare(VOID) {
  UINT32 ss0,ss1,after0,after1;VOID *prom=NULL;struct gpu_unlock_fwsec fw;
  if(Gu.started || Gu.fault || Gu.retained || Gu.allocations || Gu.profile_verified ||
     Gu.prom_verified || !Config() || !Registers(&ss0,&ss1))return EFI_NOT_READY;
  if(!GuAd104AssetsValid())return EFI_CRC_ERROR;
  LogAssets();
  prom=GuAlloc(1048576);if(!prom)return EFI_OUT_OF_RESOURCES;
  GuCopyFromIo(prom,(VOID *)(UINTN)(Gu.bar_base+0x300000),1048576);
  BOOLEAN valid=!Gu.fault && !gpu_unlock_vbios_fwsec(prom,1048576,&fw) && GuAd104FwsecSane(&fw) &&
    Config() && Registers(&after0,&after1) && ss0==after0 && ss1==after1;
  if(valid)GuLog("FWSEC from this card's VBIOS: image_off=%#x image_size=%#x imem=%#x dmem=%#x sigs=%u fuse_versions=%#x\n",
    (unsigned)fw.image_off,(unsigned)fw.image_size,(unsigned)fw.imem_size,(unsigned)fw.dmem_size,
    (unsigned)fw.sig_count,(unsigned)fw.sig_versions);
  GuFree(prom);
  if(!valid)return EFI_COMPROMISED_DATA;
  Gu.prom_verified=TRUE;
  if(!GuLatchEntrySelectors(ss0,ss1)){Gu.prom_verified=FALSE;return EFI_NOT_READY;}
  Gu.profile_verified=TRUE;return EFI_SUCCESS;
}
