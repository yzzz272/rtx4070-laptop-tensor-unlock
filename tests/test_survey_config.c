/* SPDX-License-Identifier: GPL-2.0-only */
#include "../checks.h"
#include "captured_config.h"
#include <stdio.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { checks++; if (!(x)) { \
  fprintf(stderr, "survey config FAIL line %d: %s\n", __LINE__, #x); return 1; \
} } while (0)

int main(void) {
  UINT32 config[64];
  GU_CAPS caps;
  memcpy(config, CapturedConfig, sizeof(config));

#if !defined(GU_2820_SURVEY) || !GU_PREFLIGHT_ONLY
#error Survey test must compile with read-only survey gates
#endif

  CHECK(config[0] == GU_BOARD_ID);
  CHECK(GuCheckConfig(config, 0, 1, 0, 0, &caps));
  CHECK(caps.pcie == 0x78 && caps.pm == 0x60);

  /* Survey accepts another subsystem and BDF for inventory only. */
  config[11] = 0x40691043U;
  CHECK(GuCheckConfig(config, 3, 0x7f, 31, 7, &caps));

  /* It still admits only the RTX 4070 Laptop endpoint with FLR. */
  config[0] ^= 0x00010000U;
  CHECK(!GuCheckConfig(config, 3, 0x7f, 31, 7, &caps));
  config[0] ^= 0x00010000U;
  ((UINT8 *)config)[0x0b] = 0x02;
  CHECK(!GuCheckConfig(config, 3, 0x7f, 31, 7, &caps));

  printf("survey config: %u checks PASS; subsystem/BDF open, GPU/FLR gates retained\n", checks);
  return 0;
}
