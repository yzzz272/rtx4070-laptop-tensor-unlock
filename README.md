# RTX 4070 Laptop 张量速率解锁（Windows UEFI，源码版）

这是一个面向 **RTX 4070 Laptop GPU (`10de:2820`)** 的实验性 Windows UEFI
预启动项目。它在 Windows 和 NVIDIA 驱动加载前，解除 FP16/BF16 Tensor Core
执行 FP32 累加时的半速限制。

- 不刷 VBIOS
- 不替换或修改 NVIDIA Windows 驱动
- 不修改 Windows 系统文件
- 解锁状态是易失的，完全断电后恢复原状
- 本仓库只提供源码，不附带预编译 EFI 或 NVIDIA 固件资产
- **不构建自动真实解锁镜像**；真实事务必须在启动时手动按 `U`

> 这不是功耗墙、显存容量或游戏性能解锁。主要受益的是使用
> FP16/BF16/TF32 输入并进行 FP32 累加的矩阵运算。

## 已验证硬件

真实解锁仅在以下机器上完成过匹配验证：

| 项目 | 值 |
|---|---|
| 笔记本 | MECHREVO JiguangPro Series GM5AR7O |
| GPU | RTX 4070 Laptop GPU，AD106M，36 SM |
| PCI ID | `10de:2820` |
| 子系统 | `1d05:1297` |
| BDF | `0000:01:00.0` |
| VBIOS | `95.06.15.40.5F` |
| Windows 驱动 | 617.42 |
| 芯片读数 | `PMC_BOOT_0=0x196000a1` |

精确写入准入配置在 [`target_2820.h`](target_2820.h)。除调查模式外，程序会同时
核对 PCI ID、子系统、BDF 和 FWSEC 几何；任一不匹配都会在写入前拒绝。

其他品牌、子系统、BDF 或 VBIOS 的 RTX 4070 Laptop **不能直接视为兼容**。
请先运行只读 `SURVEY2820.EFI`，不要直接修改常量后尝试真实事务。

## 实测结果

相同机器、相同 CUDA 探针、相同二进制的匹配结果：

| 状态 | FP16 输入 / FP16 累加 | FP16 输入 / FP32 累加 | 两者比值 |
|---|---:|---:|---:|
| Stock | 约 152–158 TF/s | 约 74–77 TF/s | `2.030–2.126` |
| Unlocked | 约 152–159 TF/s | 约 144–160 TF/s | `0.989–1.054` |

硬件侧同时确认：

```text
before:     READOUT_1=0x410080, full=0
selectors:  SS0=0x88888888, SS1=0x8
post-FLR:   READOUT_1=0, full=1
POST-GOP:   SS0=0x88888888, SS1=0x8
TRANSACTION OK
```

完整报告和脱敏后的成功日志位于：

- [`docs/verified-gm5ar7o.md`](docs/verified-gm5ar7o.md)
- [`docs/logs/RUN0006-success.txt`](docs/logs/RUN0006-success.txt)
- [`docs/logs/unlocked-tensor-probe.txt`](docs/logs/unlocked-tensor-probe.txt)

这证明目标 Tensor 路径实测接近翻倍，但不代表所有 AI 应用整体都能提升两倍；
实际收益还取决于算子选择、显存带宽、功耗、温度和 CPU 开销。

## 四个构建模式

`build.py` 只生成以下四个镜像：

| 镜像 | 适用范围 | GPU 写入 | 显示驱动释放 | 启动操作 |
|---|---|---:|---:|---|
| `SURVEY2820.EFI` | 任意单张 `10de:2820` | 否 | 否 | 无需按键 |
| `DRYRUN2820.EFI` | `target_2820.h` 精确目标 | 否 | 否 | 无需按键 |
| `RELTEST2820.EFI` | 精确目标 | 否 | 是 | 按 `U` |
| `UNLOCKM2820.EFI` | 精确目标 | **是** | 是 | **按 `U`** |

`SURVEY`、`DRYRUN` 和 `RELTEST` 的 GPU MMIO 写入、DMA、PCI 配置写入、Bus
Master 和 FLR 门均关闭。`RELTEST` 只验证固件显示驱动能否安全释放并恢复。

## 构建环境

需要：

- Python 3
- Zig **0.14.1**
- `zstd` 在 `PATH` 中
- 可联网下载经过 SHA-256 固定的 NVIDIA 官方输入

Windows 可安装 `zstd`：

```powershell
winget install Facebook.Zstandard
```

下载 Zig 0.14.1 后，不必全局安装，可以直接传入 `zig.exe` 路径。

## 1. 生成 NVIDIA 固件资产

本仓库不分发固件二进制。运行：

```powershell
python scripts/make_assets.py --out assets
```

脚本会下载固定版本的 NVIDIA 输入、校验 SHA-256，并生成五个文件：

```text
assets/booter_load_ad102.bin
assets/v67-ad102-610.43.03-four-plm.bin
assets/gsp_ga10x.bin
assets/gsp_boot_ad102.bin
assets/gsp_boot_desc_ad102.bin
```

## 2. 构建 EFI

```powershell
python build.py --zig C:\path\to\zig.exe --out build
```

输出写入 `build/`，并生成 `build/build-result.json`。构建过程会检查 PE/COFF
格式；`/Brepro` 使相同源码与 Zig 版本产生字节一致的镜像。

## 3. 运行离线测试

在 Git Bash、MSYS2 或 Linux 中执行。Windows 上可让 Zig 充当 C 编译器：

```sh
export CC='C:/path/to/zig.exe cc'
sh tests/run-survey-tests.sh
sh tests/run-boot-app-tests.sh assets
sh tests/run-release-tests.sh
```

完整固件事务模拟还需要目标卡的一份 1 MiB PROM 窗口：

```sh
sh tests/run-host-tests.sh /path/to/PROM-1MiB.bin assets
```

这些测试不会访问真实 GPU；PCI、MMIO、DMA、固件执行和失败场景全部由模拟器完成。

## 4. 生成 U 盘目录

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
```

会生成：

```text
stick/survey/
stick/dryrun/
stick/reltest/
stick/unlockm/
```

每个目录都包含：

```text
EFI/BOOT/BOOTX64.EFI
GPU4090-ASSETS/...
SHA256SUMS
```

`GPU4090-ASSETS` 是上游兼容路径，名称保留不代表目标 GPU 是 RTX 4090。

## 5. 准备 FAT32 U 盘

> 以下操作会清空 U 盘。务必按容量、型号和磁盘编号确认目标，绝不能误选系统盘。

建议用 Windows“磁盘管理”完成：

1. 删除测试 U 盘上的旧分区；
2. 新建一个 FAT32 主分区；
3. 一次只把某个阶段目录里的**内容**复制到 U 盘根目录；
4. 确认存在 `\EFI\BOOT\BOOTX64.EFI`；
5. 首次只能放 `survey` 或 `dryrun`，不要从 `unlockm` 开始。

切换阶段时，只需用下一阶段目录中的内容覆盖 U 盘根目录。不要同时放置多个
`EFI/BOOT/BOOTX64.EFI`。

## 6. 启动前准备

1. 保存重要数据；
2. 若启用 BitLocker/设备加密，先备份恢复密钥并暂停保护；
3. 临时关闭 Secure Boot，镜像未签名；
4. 接通笔记本电源；
5. Windows 完全关机；
6. 等电源灯熄灭后长按电源键约 10 秒；
7. 开机进入启动菜单，选择带 `UEFI` 的 USB 条目。

不要使用 Windows“重启”代替冷启动。驱动初始化后的 GPU 状态会被冷入口检查拒绝。

部分笔记本不会显示 UEFI 文字控制台。如果需要按 `U`，可在启动菜单选择 USB 并
按 Enter 后，立即连续按 `U` 约 5 秒。

## 7. 推荐分阶段流程

### 阶段 A：其他 RTX 4070 Laptop 先运行 SURVEY

适用于品牌、子系统或 VBIOS 不确定的机器。

1. 将 `stick/survey/` 内容复制到 U 盘根目录；
2. 冷启动并选择 UEFI USB；
3. 无需按键，程序只读检查后进入正常 Windows；
4. 读取 U 盘中的 `\GPU4090-UNLOCK\RUNnnnn.TXT`；
5. 保存以下行：
   - `GPU at ... subsystem=...`
   - `PMC_BOOT_0`
   - `VRAM_MIB`
   - `FWSEC geometry`
   - `release preflight`

SURVEY 不会因为子系统、BDF 或 FWSEC 几何不同而执行写入；它根本没有写入能力。
调查日志应由了解代码和硬件的人审阅，再决定是否新增独立的精确目标配置。提交信息时可使用
[`docs/compatibility-report-template.md`](docs/compatibility-report-template.md)。

### 阶段 B：DRYRUN

仅当机器匹配 `target_2820.h`，或已有经过审阅的新精确配置时运行。

成功日志应包含：

```text
PCI scan: 10de:2820 functions found=1
PCIe device capability=... FLR_capable=1
FWSEC from this card's VBIOS: ...
release preflight: status=0
Checks passed.
```

DRYRUN 不释放显示驱动，不写 GPU。

### 阶段 C：RELTEST

1. 覆盖为 `stick/reltest/`；
2. 冷启动并选择 USB；
3. 在倒计时中按 `U`，看不到文字时可立即连续按 `U`；
4. 屏幕可能短暂冻结或黑屏；
5. 成功后应正常进入 Windows。

日志应包含：

```text
choice: unlock
driver release: status=0 refresh=0 same_pci=1
release test: status=0 gop=1
```

RELTEST 仍然不能写 GPU。

### 阶段 D：UNLOCKM 真实事务

只有 DRYRUN 和 RELTEST 的日志均通过后才可进行。

1. 覆盖为 `stick/unlockm/`；
2. 冷启动并选择 USB；
3. 主动按 `U`；不按则进入未解锁的正常 Windows；
4. 等待显示恢复并进入 Windows；
5. **进入后不要立即重启**，先保存日志并运行匹配性能测试。

成功日志必须包含：

```text
selector result: SS0=0x88888888 ... matched=1
selector result: SS1=0x8 ... matched=1
AD102 selectors-applied: readout1=0 ... full=1
PCIe FLR returned: result=0
AD102 post-FLR: readout1=0 ... full=1
POST-GOP SS0=0x88888888 SS1=0x8
TRANSACTION OK
```

## 8. 成功后的性能判据

不要只看绝对 TFLOPS，因为功耗和频率会变化。至少比较同一探针的：

```text
FP16 输入 / FP16 累加吞吐
FP16 输入 / FP32 累加吞吐
两者比值
```

典型判据：

- Stock：比值约 `2.0`
- Unlocked：比值约 `1.0`

同时检查：

```powershell
nvidia-smi
```

以及 Windows 系统事件中是否出现 `nvlddmkm`、Display 或 Xid 错误。

## 停止条件与恢复

出现以下任一情况，不要继续下一阶段：

- PCI ID、子系统、BDF 或 FWSEC 几何与目标配置不一致；
- FLR 不受支持；
- `release preflight` 失败；
- 显示驱动无法恢复；
- FWSEC、权限、选择器、FLR 或 POST-GOP 回读不匹配；
- Windows 出现设备错误、Xid、花屏或持续黑屏。

如果屏幕显示 `STOPPED. Power OFF with the power button.`，或真实事务后长时间无法
进入 Windows：

1. 长按电源键彻底断电；
2. 拔掉 U 盘；
3. 再次开机选择原来的 Windows Boot Manager。

所有修改都是易失的，完全断电会恢复 stock 状态。

## 关于自动启动

本项目故意不构建自动真实解锁镜像，也不提供修改内置 ESP/BootOrder 的安装脚本。
完成多次冷启动和实际工作负载稳定性验证前，不建议自动化。自动化不会让解锁永久化，
它只是每次开机自动重复 UEFI 事务。

## 项目结构

```text
target_2820.h          精确写入目标配置
build.py               可复现 EFI 构建
scripts/make_assets.py 从固定 NVIDIA 输入生成资产
scripts/make_stick.py  生成四阶段 U 盘目录
firmware/              固件下载、校验与生成器
vendor/                上游保留的事务核心和 EDK2 头文件
compat/                UEFI 兼容层
tests/                 模拟 PCI/MMIO/DMA/失败场景测试
docs/                  已验证机器的报告、日志和性能结果
```

## 来源与许可

代码许可证为 GPL-2.0-only。保留了上游许可、来源和第三方说明：

- `JustAResearcher/gpu-unlock-ada`
- `MarvinFS/rtx4090-uefi`
- `NekoMirra/rtx4060-laptop-tensor-unlock`
- `Zagitta/gpu-unlock`
- EDK2 头文件及 NVIDIA 输入的各自许可

详见 `LICENSE*`、`THIRD_PARTY_NOTICES.md`、`UPSTREAM-WINDOWS-NOTICES.md`、
`NVIDIA-FILES.md` 和 `provenance.json`。

## 免责声明

这是实验性硬件研究代码，可能导致黑屏、启动失败、驱动异常或数据丢失。不要把一个
机型的成功结果外推到其他笔记本。不要删除精确准入检查来“试试看”。使用者必须能够
完全断电、进入固件启动菜单并恢复原始 Windows 启动路径。
