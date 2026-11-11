# RTX 4070 Laptop 张量速率解锁（Windows UEFI）

[English](README.md) | **简体中文**

> ## ⚠️ 本项目由 AI 生成，使用前请自行辨别
>
> 本仓库的代码、构建脚本、测试和本文档都在 AI 的深度参与下生成。它在下文
> 描述的那一台机器上完成过构建和实机测试，但**没有**经过安全专业人员的评审，
> 而 AI 生成的系统级代码可能以难以察觉的方式出错。
>
> 运行任何镜像前请先读源码。不要在无法承受损失的机器上运行。不要把这里的
> 跑分当作对你硬件的承诺。如果你没有能力判断这些 C 与 UEFI 代码，请找人帮你
> 审阅。

一个在 Windows 启动前运行的 UEFI 程序，用于解除消费级 Ada 笔记本 GPU 上
「FP16/BF16 Tensor Core 以 FP32 累加」时的半速限制。

- **不**刷写 VBIOS
- **不**替换或修改 NVIDIA Windows 驱动
- **不**修改 Windows 系统文件
- **不**安装启动项，也不碰内置 ESP
- 解锁状态是**易失**的：完全断电后恢复原状

这不是功耗墙、显存容量或游戏性能解锁。它只对「FP16/BF16/TF32 输入 + FP32
累加」的矩阵运算有帮助。

---

## 验证范围 —— 请先读这一节

完整验证过的机器**只有一台**：

| 项目 | 值 |
|---|---|
| 笔记本 | MECHREVO JiguangPro Series **GM5AR7O** |
| GPU | RTX 4070 Laptop GPU，AD106M，36 SM |
| PCI ID | `10de:2820` |
| 子系统 | `1d05:1297` |
| BDF | `0000:01:00.0` |
| VBIOS | `95.06.15.40.5F` |
| 芯片读数 | `PMC_BOOT_0=0x196000a1` |
| NVIDIA 驱动 | 617.42 |
| Windows | 10 Pro N for Workstations 19045 |

**其他任何 RTX 4070 Laptop 都未经验证。** 品牌、子系统、BDF、VBIOS 版本、
EC 与固件行为都会改变结果。这台机器上的成功不能说明你的机器也会成功。

如果你的机器不是上表这一台，唯一受支持的第一步是只读的 `SURVEY2820`：

1. 构建 `SURVEY2820.EFI`，从 U 盘启动。
2. 它会记录你的子系统、BDF、芯片读数、显存和 FWSEC 几何，然后正常进入 Windows。
3. 它无法写入 GPU：所有写入、DMA、Bus Master、PCI 配置写入、显示释放和 FLR
   门在编译期就是关闭的。
4. 按 [`docs/compatibility-report-template.md`](docs/compatibility-report-template.md)
   填写报告并开 issue。

只有在日志被审阅之后，才会为新机器建立独立的精确目标配置。自己改常量、跳过
这一步，是让人把笔记本变砖的常见方式。

---

## 已验证机器上的实测结果

同一台机器、同一个 CUDA 探针、同样的矩阵形状：

| 状态 | FP16 输入 / FP16 累加 | FP16 输入 / FP32 累加 | 比值 |
|---|---:|---:|---:|
| 原始 | 约 152–158 TF/s | 约 74–77 TF/s | `2.030–2.126` |
| 解锁 | 约 152–159 TF/s | 约 144–160 TF/s | `0.989–1.054` |

作为对照的 FP16 累加几乎不变，而 FP32 累加路径接近翻倍。硬件回读同样一致：

```text
before:     READOUT_1=0x410080  full=0
selectors:  SS0=0x88888888  SS1=0x8
post-FLR:   READOUT_1=0  full=1
POST-GOP:   SS0=0x88888888  SS1=0x8
TRANSACTION OK
```

仓库内的证据：

- [`docs/verified-gm5ar7o.md`](docs/verified-gm5ar7o.md)
- [`docs/logs/RUN0006-success.txt`](docs/logs/RUN0006-success.txt) —— 手动镜像
- [`docs/logs/RUN0001-auto-success.txt`](docs/logs/RUN0001-auto-success.txt) —— 自动镜像
- [`docs/logs/unlocked-tensor-probe.txt`](docs/logs/unlocked-tensor-probe.txt)

这些数字来自一台笔记本、一套散热设计。请预期降频，而不是所有应用都白得 2 倍。

---

## 原理简述

消费级 Ada 的 FP32 累加张量路径只有 FP16 累加的一半速率。这条限制由两个易失
速度选择器（`SS0`、`SS1`）和四个 PLM 权限寄存器决定，只有 NVIDIA 自己的签名
固件链能打开它们。

在 Windows 启动前，程序会：

1. 从 `BAR0+0x300000` 读取这块卡自己的 VBIOS，解析 FWSEC 描述符。
2. 加载签名 GSP Falcon 固件建立 WPR2。
3. 在 SEC2 上运行固定版本的 AD102 家族 Booter 与四 PLM payload，打开
   `WPR_CFG`、`WPR` 和 `FEAT_OVR_PLM`。
4. 写入 `SS0=0x88888888`、`SS1=0x8`，并回读确认。
5. 执行一次 PCIe Function Level Reset，确认选择器仍然保持。
6. 重连固件显示驱动，交棒给原有的 Windows Boot Manager。

因为选择器是易失寄存器，每次冷启动都要重新执行。

---

## 构建模式

`build.py` 默认生成四个镜像，加 `--with-auto` 会多生成一个。

| 镜像 | 准入目标 | GPU 写入 | 显示释放 | 按键 |
|---|---|---:|---:|---|
| `SURVEY2820.EFI` | 任意单张 `10de:2820` | 否 | 否 | 无 |
| `DRYRUN2820.EFI` | 精确配置 | 否 | 否 | 无 |
| `RELTEST2820.EFI` | 精确配置 | 否 | 是 | `U` |
| `UNLOCKM2820.EFI` | 精确配置 | **是** | 是 | **`U`** |
| `UNLOCKA2820.EFI` | 精确配置 | **是** | 是 | 无（3 秒） |

「精确配置」指 PCI ID、子系统、BDF 和 FWSEC 几何必须同时匹配
[`target_2820.h`](target_2820.h)。任何一项不符都会在第一次写入前被拒绝。

`UNLOCKA2820` 需要显式开启。倒计时期间按 `Esc` 打开两项菜单，按 `S` 进入未解锁
的 Windows。

---

## 环境要求

- Python 3
- Zig **0.14.1**
- `zstd` 在 `PATH` 中（仅用于生成固件资产）
- 可联网下载固定版本的 NVIDIA 输入

```powershell
winget install Facebook.Zstandard
```

Zig 不必全局安装，直接传可执行文件路径即可。

---

## 构建

### 1. 生成固件资产

本仓库不分发 NVIDIA 的二进制文件。

```powershell
python scripts/make_assets.py --out assets
```

脚本会下载固定输入、校验 SHA-256，并把五个文件与 NVIDIA 许可写入 `assets/`。

### 2. 构建镜像

```powershell
python build.py --zig C:\path\to\zig.exe --out build
# 可选：自动镜像
python build.py --zig C:\path\to\zig.exe --out build --with-auto
```

输出在 `build/`，并生成 `build/build-result.json`。镜像会做 PE 校验，并使用
`/Brepro`，因此相同源码与 Zig 版本产生完全相同的字节。

### 3. 可复现性校验

```powershell
python tools/check_reference_build.py
```

它会把你的构建与 [`docs/reference-build-result.json`](docs/reference-build-result.json)
对比。当前源码可逐字节复现全部五个记录镜像，包括两个在实机上运行过的镜像：

| 镜像 | SHA-256（前 16 位） |
|---|---|
| `SURVEY2820.EFI` | `bb4c3368402d52f0` |
| `DRYRUN2820.EFI` | `cf98446deb858daa` |
| `RELTEST2820.EFI` | `0d640e93a585c03e` |
| `UNLOCKM2820.EFI` | `2929454ea73fe85b` |
| `UNLOCKA2820.EFI` | `58085a8d9f9dce0d` |

CI 会执行同样的对比，因此任何改变输出的改动都会被明确指出。

---

## 测试

所有测试都是模拟的：PCI、MMIO、DMA、固件执行和失败路径都跑在假引擎上，不会
接触真实 GPU。

```sh
export CC='C:/path/to/zig.exe cc'

sh tests/run-survey-tests.sh
sh tests/make_placeholder_assets.sh /tmp/assets
sh tests/run-boot-app-tests.sh /tmp/assets
sh tests/run-release-tests.sh
```

完整事务模拟还需要目标卡的 1 MiB PROM 窗口和真实固件资产：

```sh
sh tests/run-host-tests.sh /path/to/PROM-1MiB.bin assets
```

这两项都不随仓库发布，所以该套件只在本地运行；CI 运行其余三套。

---

## 制作 U 盘

> 这会清空 U 盘。执行任何破坏性操作前，请确认磁盘编号、型号和容量。
> 绝不要选中系统盘。

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
# 只生成一个阶段
python scripts/make_stick.py --build build --assets assets --out stick --variant dryrun
```

每个阶段目录包含：

```text
EFI/BOOT/BOOTX64.EFI
GPU4090-ASSETS/...
SHA256SUMS
```

把某个阶段目录里的**内容**复制到 FAT32 U 盘根目录。同一时间只能存在一个
`EFI/BOOT/BOOTX64.EFI`。

`GPU4090-ASSETS` 和 `GPU4090-UNLOCK` 是上游遗留的路径名。保留它们是因为改名会
改变实机验证过的镜像字节。

---

## 分阶段流程

不要跳阶段。每个阶段的存在，都是为了让失败停在写入 GPU 之前。

### 每次启动前

1. 备份重要数据。
2. 若启用了 BitLocker 或设备加密，先备份恢复密钥并暂停保护。
3. 关闭 Secure Boot（镜像未签名）。
4. 关闭 Windows 快速启动。
5. 接上电源适配器。
6. 完全关机。
7. 等电源灯熄灭后，长按电源键约 10 秒。
8. 开机进入固件启动菜单（验证机上是 F7），选择名字里带 `UEFI` 的那一项。

不要用 Windows 的「重启」代替冷启动。驱动已经初始化过的 GPU 会被冷入口检查拒绝。

有些笔记本根本不显示文字控制台。需要按键的阶段，在选中 U 盘条目并按 Enter 后，
立即连续按对应按键几秒。

### 阶段 A —— `SURVEY2820`（任意 4070 Laptop）

无需按键。它记录硬件事实后进入 Windows。把生成的
`\GPU4090-UNLOCK\RUNnnnn.TXT` 发回审阅。

### 阶段 B —— `DRYRUN2820`（仅精确配置）

无需按键，不释放显示，不写 GPU。正常日志包含：

```text
PCI scan: 10de:2820 functions found=1
PCIe device capability=... FLR_capable=1
FWSEC from this card's VBIOS: image_off=... image_size=...
release preflight: status=0
Checks passed.
```

### 阶段 C —— `RELTEST2820`

倒计时期间按 `U`。屏幕可能冻结或黑屏。正常日志包含：

```text
choice: unlock
driver release: status=0 refresh=0 same_pci=1
release test: status=0 gop=1
```

仍然不写 GPU。

### 阶段 D —— `UNLOCKM2820`（真实事务）

只有 B 和 C 都通过后才能进行。按 `U`。正常日志包含：

```text
selector result: SS0=0x88888888 ... matched=1
selector result: SS1=0x8 ... matched=1
AD102 selectors-applied: readout1=0 ... full=1
PCIe FLR returned: result=0
AD102 post-FLR: readout1=0 ... full=1
POST-GOP SS0=0x88888888 SS1=0x8
TRANSACTION OK
```

之后先留在 Windows 里测量，不要立刻重启。

---

## 判断是否成功

不要只看绝对 TFLOPS，频率和功耗上限会变化。用同一个二进制比较
FP16 累加与 FP32 累加的吞吐比值：

- 原始：约 `2.0`
- 解锁：约 `1.0`

同时检查：

```powershell
nvidia-smi
```

并在 Windows 系统日志里查找 `nvlddmkm`、`Display` 或 Xid 错误。

---

## 停止条件与恢复

出现以下任一情况，停止，不要进入下一阶段：

- PCI ID、子系统、BDF 或 FWSEC 几何与目标配置不一致
- 不支持 FLR
- `release preflight` 失败
- 显示驱动无法恢复
- 任何选择器、权限、FLR 或 POST-GOP 回读不匹配
- Windows 报设备错误、Xid、花屏或持续黑屏

如果屏幕显示 `STOPPED. Power OFF with the power button.`，或真实事务后约两分钟
仍未进入 Windows：

1. 长按电源键直到完全断电。
2. 拔掉 U 盘。
3. 启动原来的 Windows Boot Manager。

所有修改都是易失的，完全断电即恢复原状。

睡眠唤醒、驱动重启或驱动更新后，解锁也会丢失；重新用 U 盘启动即可再次解锁。

---

## 关于自动化

默认构建不生成自动真实解锁镜像，也不提供修改内置 ESP 或固件启动顺序的安装器。
自动化不会让解锁永久化，它只是在每次开机时重复一次 UEFI 事务。

如果确实需要「插上 U 盘、开机就解锁」：

```powershell
python build.py --zig C:\path\to\zig.exe --out build --with-auto
python scripts/make_stick.py --build build --assets assets --out stick --variant auto
```

然后在固件里把该 U 盘排在 Windows Boot Manager 之前。拔掉 U 盘应回退到 Windows。
自动镜像同样只接受精确目标配置。

---

## 仓库结构

```text
target_2820.h                  精确写入目标
build.py                       可复现构建（--with-auto 增加自动镜像）
tools/check_reference_build.py 校验构建与记录哈希是否一致
scripts/make_assets.py         从固定 NVIDIA 输入生成固件资产
scripts/make_stick.py          生成分阶段 U 盘目录
firmware/                      下载、校验与生成脚本
vendor/                        保留的事务核心与 EDK2 头文件
compat/                        UEFI 兼容层
tests/                         模拟 PCI/MMIO/DMA/失败场景测试
docs/                          硬件报告、日志、参考哈希
```

---

## 来源与许可

代码许可为 GPL-2.0-only。上游项目及其许可记录在 `LICENSE*`、
`THIRD_PARTY_NOTICES.md`、`UPSTREAM-WINDOWS-NOTICES.md`、`NVIDIA-FILES.md`
和 `provenance.json` 中。

本仓库基于以下上游工作：

- `JustAResearcher/gpu-unlock-ada`
- `MarvinFS/rtx4090-uefi`
- `NekoMirra/rtx4060-laptop-tensor-unlock`
- `Zagitta/gpu-unlock`
- EDK2 头文件（遵循其自身许可）
- NVIDIA 固件输入（遵循 NVIDIA 自身许可，本地下载，不随仓库分发）

---

## 免责声明

实验性硬件研究代码，在 AI 协助下编写，仅在一款笔记本上验证过。它可能导致黑屏、
启动失败、驱动异常或数据丢失。一台机器上的结果不能迁移到另一台。不要为了
「让它跑起来」而删除精确目标检查。你必须有能力切断电源、进入固件启动菜单并
启动原来的 Windows 条目。

不提供任何形式的担保。运行它的人是你，责任也在你。
