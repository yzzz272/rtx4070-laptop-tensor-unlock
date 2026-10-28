/* SPDX-License-Identifier: GPL-2.0-only */
#pragma once

/*
 * Exact write-enabled target profile.
 *
 * SURVEY2820 ignores the subsystem, BDF and exact FWSEC values below while
 * keeping every write/DMA/FLR gate closed. DRYRUN2820, RELTEST2820 and
 * UNLOCKM2820 enforce every value.
 */
#define GU_TARGET_NAME "MECHREVO GM5AR7O RTX 4070 Laptop"
#define GU_TARGET_PCI_TEXT "10de:2820"
#define GU_BOARD_ID 0x282010deU
#define GU_SUBSYSTEM_ID 0x12971d05U /* PCI subsystem 1d05:1297, wire dword 0x12971d05 */
#define GU_TARGET_SEGMENT 0U
#define GU_TARGET_BUS 1U
#define GU_TARGET_DEVICE 0U
#define GU_TARGET_FUNCTION 0U
#define GU_TARGET_VBIOS "95.06.15.40.5F" /* documentation only; FWSEC geometry is enforced */

#define GU_FWSEC_IMAGE_OFF 0x46888U
#define GU_FWSEC_IMAGE_SIZE 0x10300U
#define GU_FWSEC_IMEM_PA 0U
#define GU_FWSEC_IMEM_SIZE 0xf500U
#define GU_FWSEC_IMEM_VA 0U
#define GU_FWSEC_DMEM_PA 0U
#define GU_FWSEC_DMEM_SIZE 0xd80U
#define GU_FWSEC_PKC_OFF 0xb24U
#define GU_FWSEC_INTERFACE_OFF 0x1cU
#define GU_FWSEC_UCODE_ID 9U
#define GU_FWSEC_ENGINE_MASK 0x400U
#define GU_FWSEC_SIG_COUNT 2U
#define GU_FWSEC_SIG_VERSIONS 0x3U
#define GU_FWSEC_SIG_BYTES 768U
