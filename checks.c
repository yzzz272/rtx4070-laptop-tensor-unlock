/* Modified 2026-10-19/20 for Windows GPU UNLOCK; changes documented in CHANGES.md. */ #include "checks.h"
#include <IndustryStandard/Pci.h>

#define GU_CONFIG_BYTES 256U
#define GU_CAP_START 0x40U
#define GU_CAP_LAST 0xfcU
#define GU_CAP_LIMIT ((GU_CONFIG_BYTES - GU_CAP_START) / 4U)
#define GU_MSIX_ID 0x11U

static UINT8 ConfigByte(const UINT32 Config[64], UINTN Offset) {
  return (UINT8)(Config[Offset / 4U] >> ((Offset & 3U) * 8U));
}

static UINT16 ConfigWord(const UINT32 Config[64], UINTN Offset) {
  return (UINT16)(ConfigByte(Config, Offset) |
                  ((UINT16)ConfigByte(Config, Offset + 1U) << 8U));
}

/* All builds require the RTX 4070 Laptop PCI ID, endpoint shape, memory decode,
 * FLR and D0. Write-capable profiles additionally pin subsystem and BDF;
 * GU_2820_SURVEY intentionally leaves those two values open while all writes stay closed. */
BOOLEAN GuCheckConfig(const UINT32 Config[64], UINTN Segment, UINTN Bus,
                      UINTN Device, UINTN Function, GU_CAPS *Out) {
  GU_CAPS Caps = {0, 0, 0, 0, 0};
  UINT64 Seen = 0;
  UINTN Pointer, Steps = 0;
  UINT16 Command;

  if (Out == NULL) return FALSE;
  *Out = Caps;
  if (Config == NULL) return FALSE;
  if (Config[0] != GU_BOARD_ID ||
#if !defined(GU_2820_SURVEY)
      Segment != GU_TARGET_SEGMENT || Bus != GU_TARGET_BUS ||
      Device != GU_TARGET_DEVICE || Function != GU_TARGET_FUNCTION ||
      Config[11] != GU_SUBSYSTEM_ID ||
#endif
      ConfigByte(Config, 0x0b) != PCI_CLASS_DISPLAY ||
      (ConfigByte(Config, PCI_HEADER_TYPE_OFFSET) & 0x7fU) != HEADER_TYPE_DEVICE)
    return FALSE;
  /* Bus master may be set by the board firmware; the release step clears it (as the Linux module does). */
  Command = ConfigWord(Config, PCI_COMMAND_OFFSET);
  if ((Command & EFI_PCI_COMMAND_MEMORY_SPACE) == 0 ||
      (ConfigWord(Config, PCI_PRIMARY_STATUS_OFFSET) & EFI_PCI_STATUS_CAPABILITY) == 0)
    return FALSE;

  Pointer = ConfigByte(Config, PCI_CAPABILITY_POINTER_OFFSET);
  while (Pointer != 0) {
    UINT64 Bit;
    UINT8 Id, Next;
    UINT16 Control;
    /* A list that loops, leaves the standard area or is misaligned cannot be trusted for offsets. */
    if (++Steps > GU_CAP_LIMIT || Pointer < GU_CAP_START || Pointer > GU_CAP_LAST || (Pointer & 3U) != 0)
      return FALSE;
    Bit = (UINT64)1U << (Pointer / 4U);
    if ((Seen & Bit) != 0) return FALSE;
    Seen |= Bit;
    Id = ConfigByte(Config, Pointer);
    Next = ConfigByte(Config, Pointer + 1U);
    Control = ConfigWord(Config, Pointer + 2U);
    switch (Id) {
      case EFI_PCI_CAPABILITY_ID_PMI:
        if (Caps.pm == 0) {
          if ((ConfigWord(Config, Pointer + 4U) & 3U) != PCI_POWER_STATE_D0) return FALSE;
          Caps.pm = (UINT16)Pointer;
        }
        break;
      case EFI_PCI_CAPABILITY_ID_MSI:
        if (Caps.msi == 0) Caps.msi = (UINT16)Pointer;
        break;
      case PCI_EXPRESS_CAPABILITY_ID:
        if (Caps.pcie == 0) {
          /* FLR support (device capabilities bit 28) is what the transaction's final reset relies on. */
          if ((Control & 0x0fU) < 1 || (Config[(Pointer + 4U) / 4U] & (1U << 28U)) == 0) return FALSE;
          Caps.pcie = (UINT16)Pointer;
          Caps.pcie_version = (UINT8)(Control & 0x0fU);
        }
        break;
      case GU_MSIX_ID:
        if (Caps.msix == 0) Caps.msix = (UINT16)Pointer;
        break;
      default:
        break;
    }
    Pointer = Next;
  }
  if (Caps.pcie == 0) return FALSE;
  *Out = Caps;
  return TRUE;
}
