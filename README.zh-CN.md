# RTX 4070 Laptop 张量速率解锁（Windows UEFI）

[English](README.md) | **简体中文**

一个面向 **RTX 4070 Laptop GPU（`10de:2820`）** 的 UEFI 程序，在 Windows 与
NVIDIA 驱动加载之前，解除 FP16/BF16 张量运算以 FP32 累加时的半速限制。

不刷写 VBIOS，不替换 NVIDIA 驱动，不修改 Windows 系统文件。

> **由 AI 生成，使用前请自行辨别。** 代码、脚本、测试和本文档都在 AI 的深度
> 参与下写成。它们在下表那台机器上构建并实机运行过，但没有经过安全专业人员的
> 评审。运行前请先读源码，也不要在无法承受损失的机器上运行。

## 已验证硬件

| | |
|---|---|
| 笔记本 | MECHREVO JiguangPro Series GM5AR7O |
| GPU | RTX 4070 Laptop，AD106M，36 SM |
| PCI / 子系统 | `10de:2820` / `1d05:1297` |
| BDF | `0000:01:00.0` |
| VBIOS | `95.06.15.40.5F` |
| 芯片读数 | `PMC_BOOT_0=0x196000a1` |
| 驱动 | NVIDIA 617.42，Windows 10 19045 |

这是唯一验证过的机器。其他 RTX 4070 Laptop 的子系统、BDF、VBIOS 和固件行为
都可能不同。那些机器先跑 `SURVEY2820`：它是只读的，记录卡的标识与 FWSEC 几何，
然后进入 Windows。

## 实测数据

同一台机器、同一个 CUDA 探针、8192³ GEMM、20 次取中位数：

| 模式 | 原始 | 解锁 |
|---|---:|---:|
| FP16 输入 / FP16 累加 | 152–158 TF/s | 152–159 TF/s |
| FP16 输入 / FP32 累加 | 74–77 TF/s | 144–160 TF/s |
| BF16 输入 / FP32 累加 | 74–77 TF/s | 145–158 TF/s |
| TF32 | 38–40 TF/s | 76–80 TF/s |
| FP32 SIMT（对照） | 17.6–19.1 TF/s | 17.6–19.1 TF/s |

FP16 累加是对照组，它不动；FP32 累加路径接近翻倍，所以
`FP16累加 / FP32累加` 的比值从约 `2.0` 变成约 `1.0`。

寄存器侧判据（启动日志）：

```text
AD102 before-firmware: readout1=0x410080 fields=0 0 2 0 0 2 0 2 0 valid=1 full=0
selector result: SS0=0x88888888 matched=1
selector result: SS1=0x8 matched=1
AD102 selectors-applied: readout1=0 fields=0 0 0 0 0 0 0 0 0 valid=1 full=1
PCIe FLR returned: result=0
AD102 post-FLR: readout1=0 fields=0 0 0 0 0 0 0 0 0 valid=1 full=1
POST-GOP SS0=0x88888888 SS1=0x8
TRANSACTION OK
```

完整日志：[`docs/logs/RUN0006-success.txt`](docs/logs/RUN0006-success.txt)、
[`docs/logs/RUN0001-auto-success.txt`](docs/logs/RUN0001-auto-success.txt)、
[`docs/logs/unlocked-tensor-probe.txt`](docs/logs/unlocked-tensor-probe.txt)。

解锁后的瓶颈是功耗和散热，不是速率限制：115 W 的功耗预算会先压住持续频率。

## 原理

消费级 Ada 卡的 FP32 累加张量路径只有 FP16 累加的一半速率。这条限制由两个
易失速度选择器（`SS0`、`SS1`）和四个 PLM 权限寄存器决定，只有 NVIDIA 自己的
签名固件链能打开它们。程序在 Windows 引导前：

1. 读卡自身 VBIOS（`BAR0+0x300000`，1 MiB）解析 FWSEC 描述符；
2. 用签名 GSP Falcon 加载 FWSEC 建立 WPR2；
3. 在 SEC2 上运行 AD102 家族 Booter 与四 PLM payload，把 `WPR_CFG`、`WPR`、
   `FEAT_OVR_PLM` 打开；
4. 写 `SS0=0x88888888`、`SS1=0x8`，回读确认生效；
5. 做一次 PCIe FLR，确认选择器保持；
6. 重连固件显示驱动，交棒原有的 Windows Boot Manager。

选择器是易失寄存器，完全断电后回到原值，所以每次冷启动都要跑一次。这不是永久
修改硬件，也无法改成永久——那需要改写卡上签名的固件。

## 相对上游的改动

| 文件 | 改动 |
|---|---|
| `target_2820.h` | 新增：精确目标配置——PCI ID、子系统、BDF、FWSEC 几何 |
| `checks.c`、`profile.c`、`port.c` | 固定子系统、BDF 与 FWSEC 几何；`GU_2820_SURVEY` 放宽这三项但保持所有写入门关闭 |
| `app.c` | 目标改为 `10de:2820`，RTX 4070 Laptop 文案 |
| `vendor/prep_610.h` | 在固定 Booter 家族中加入 `GU_AD106M_RTX_4070_LAPTOP 0x2820` |
| `build.py` | 五个变体；`--safe-only` 去掉自动镜像 |
| `scripts/make_stick.py` | 默认即插即用布局，`--layout staged` 生成分阶段目录 |
| `scripts/usb_boot_entry.ps1` | 新增：可撤销的 U 盘固件启动项 |
| `tools/check_reference_build.py` | 新增：构建与记录哈希的对比 |
| `tests/` | 本机夹具；SURVEY 准入测试 |

写入门在任何地方都没有放宽：`SURVEY2820` 根本不存在 MMIO 写入、DMA、Bus
Master、PCI 配置写入、显示释放和 FLR 路径；其余四个镜像在第一次写入前就会因为
任一固定值不匹配而拒绝。

## 环境要求

- Windows 10 或 11，UEFI 引导，**Secure Boot 关闭**（镜像未签名）
- 恰好一张 `10de:2820`
- 一个可以清空的 U 盘——FAT32，128 MB 就够
- 关闭快速启动：`powercfg /h off`
- 启用 BitLocker 时先挂起：`Suspend-BitLocker -MountPoint C: -RebootCount 3`
- 构建需要 Python 3、Zig **0.14.1**，以及 `PATH` 中的 `zstd`

## 构建

### 复现已记录的镜像

```powershell
python scripts/make_assets.py --out assets
python build.py --zig C:\path\to\zig.exe --out build
python tools/check_reference_build.py
```

第三条命令把你的构建与
[`docs/reference-build-result.json`](docs/reference-build-result.json) 对比。
当前源码可逐字节复现全部五个镜像，包括两个实机运行过的镜像。CI 执行同样的检查。

### 只构建安全镜像

```powershell
python build.py --zig C:\path\to\zig.exe --out build --safe-only
```

去掉 `UNLOCKA2820`，它是唯一无需按键就会解锁的镜像。

### 固件资产

`assets/` 在本地生成，NVIDIA 的文件不随仓库分发。

```text
booter_load_ad102.bin                 57672  sha256 6ee05b20e1dc244c...
v67-ad102-610.43.03-four-plm.bin      64000  sha256 44c36b2d6b3424e5...
gsp_ga10x.bin                      84277400  sha256 572373620a37418f...
gsp_boot_ad102.bin                    36864  sha256 45d6335a8185d6ff...
gsp_boot_desc_ad102.bin                  84  sha256 83f8f3f1f5f9496e...
```

`scripts/make_assets.py` 会下载固定版本的 NVIDIA `610.43.03` 输入，校验 SHA-256
后生成这五个文件。

## 镜像

| 镜像 | 写入 GPU | 释放显示 | 按键 |
|---|---:|---:|---|
| `SURVEY2820.EFI` | 否 | 否 | 无 |
| `DRYRUN2820.EFI` | 否 | 否 | 无 |
| `RELTEST2820.EFI` | 否 | 是 | `U` |
| `UNLOCKM2820.EFI` | 是 | 是 | `U` |
| `UNLOCKA2820.EFI` | 是 | 是 | 无（3 秒） |

## U 盘

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
```

把 `stick\` 里的**内容**复制到 FAT32 U 盘根目录。根目录镜像是自动版，其余四个
放在 `RECOVERY\`。

```text
EFI/BOOT/BOOTX64.EFI     UNLOCKA2820
GPU4090-ASSETS/          五个固件文件
RECOVERY/                其余四个镜像
README-AUTO.txt
SHA256SUMS
```

`GPU4090-ASSETS` 和 `GPU4090-UNLOCK` 是上游遗留的路径名。改名会改变实机验证过的
镜像字节。

### 即插即用

```powershell
# 预演：只显示将要做什么
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1
# 创建启动项并排到第一位
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply
```

| 状态 | 结果 |
|---|---|
| 插着 U 盘冷启动 | 固件启动 U 盘，解锁，进入 Windows |
| 拔掉 U 盘冷启动 | 固件回退到 Windows Boot Manager，GPU 保持原始 |

脚本只在以下条件全部成立时动手：卷是可移动 FAT32、卷标符合预期、根目录镜像是
发布版自动镜像（校验 SHA-256）、Secure Boot 已关闭、且没有已记录的启动项。它把
启动项 GUID 记录在 `%ProgramData%\Rtx4070Unlock\usb-entry.json`，
`-Remove -Apply` 可以精确撤销。

首次启动：完全关机，等电源灯熄灭，长按电源键 10 秒，再开机并打开启动菜单
（验证机上是 F7）。倒计时内 `Esc` 打开菜单，`S` 进入未解锁的 Windows，`U`
立即解锁。

通过准入的第一轮日志：

```text
PCI scan: 10de:2820 functions found=1
PCIe device capability=... FLR_capable=1
FWSEC from this card's VBIOS: image_off=0x46888 image_size=0x10300 ...
release preflight: status=0
Checks passed.
```

### 分阶段验证

不是验证过的那台机器时，不要从自动镜像开始。

```powershell
python scripts/make_stick.py --layout staged --out stick
```

1. `SURVEY2820`——只读。把 `\GPU4090-UNLOCK\RUNnnnn.TXT` 发来审阅。
2. `DRYRUN2820`——仅精确目标。应看到 `Checks passed.`
3. `RELTEST2820`——按 `U`。应看到 `release test: status=0 gop=1`。
4. `UNLOCKM2820`——按 `U`。应看到 `TRANSACTION OK`。

## 验证

```powershell
python tools/check_reference_build.py
nvidia-smi
```

吞吐：用同一个二进制比较 FP16 累加与 FP32 累加。原始约 `2.0`，解锁约 `1.0`。
同时在 Windows 系统日志里查找 `nvlddmkm`、`Display` 或 Xid 错误。

## 卸载与恢复

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Remove -Apply
```

除此之外没有安装任何东西：内置磁盘上没有文件，Windows 里没有启动项，驱动没有改动。

真实事务后黑屏或进不去 Windows：长按电源键直到断电，拔掉 U 盘，在固件启动菜单
（本机 F7）选择 `Windows Boot Manager`。完全断电即恢复原状。

## 已知限制

- 单机、单 VBIOS（`95.06.15.40.5F`）、单厂商验证。其他 AD106M 板卡必须先通过
  SURVEY，并建立自己的精确配置。
- 功耗与散热限制收益：115 W 会先压住持续频率，张量路径不再是瓶颈。
- 解锁是易失的。睡眠唤醒、驱动重启或驱动更新都会回到原始状态，只有经 U 盘的
  冷启动能恢复。
- 快速启动必须保持关闭，否则 Windows 的「关机」会跳过固件启动路径，U 盘根本
  不会运行。
- 有些笔记本把启动项绑定到某个 USB 端口；启动项失效时重新执行 `-Apply`。
- 固件报「no boot device」而不回退时，需要删掉启动项，改为每次用启动菜单选。
- 默认会构建 `UNLOCKA2820`。不想要无需按键的镜像就用 `--safe-only`。

## 许可与来源

代码许可为 GPL-2.0-only。许可与上游声明见 `LICENSE*`、`THIRD_PARTY_NOTICES.md`、
`UPSTREAM-WINDOWS-NOTICES.md`、`NVIDIA-FILES.md`、`provenance.json`。

上游：
- `JustAResearcher/gpu-unlock-ada`——Ada 资产、Booter 与四 PLM payload
- `MarvinFS/rtx4090-uefi`——本仓库所源自的 Windows UEFI 移植
- `NekoMirra/rtx4060-laptop-tensor-unlock`——本移植的直接基线
- `Zagitta/gpu-unlock`——机制最初实现
- EDK2 头文件，遵循其自身许可

`assets/` 里的五个文件是 NVIDIA 的签名固件，按 NVIDIA 自身许可在本地下载，不随
仓库分发。

实验性研究代码，仅在一款笔记本上验证，不提供任何担保。它可能导致黑屏、启动失败、
驱动异常或数据丢失。运行它的人是你，责任也在你。
