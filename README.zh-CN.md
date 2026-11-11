# RTX 4070 Laptop 张量速率解锁（Windows UEFI）

[English](README.md) | **简体中文**

一个在 Windows 之前运行的 UEFI 程序，在一台已验证的笔记本上解除
「FP16/BF16 张量运算以 FP32 累加」时的半速限制。

它不刷 VBIOS、不改驱动、不改 Windows 文件、不安装启动项。解锁是易失的：
完全断电即恢复原状。

> **由 AI 生成，使用前请自行辨别。**
> 代码、脚本、测试和本文档都在 AI 的深度参与下写成。它们在下表那台机器上
> 构建并实机运行过，但没有经过安全专业人员的评审。运行前请先读源码，也不要
> 在无法承受损失的机器上运行。

## 适用范围

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
都可能不同，结果未知。

如果你的机器不是这一台，先跑 `SURVEY2820`。它是只读的：所有写入、DMA、
Bus Master、PCI 配置写入、显示释放和 FLR 路径在编译期就被移除。它会记录你的
子系统、BDF、芯片读数、显存和 FWSEC 几何，然后进入 Windows。把日志发到
issue 里，再做其他尝试。

## 实测结果

| 状态 | FP16 输入 / FP16 累加 | FP16 输入 / FP32 累加 | 比值 |
|---|---:|---:|---:|
| 原始 | 152–158 TF/s | 74–77 TF/s | 2.03–2.13 |
| 解锁 | 152–159 TF/s | 144–160 TF/s | 0.99–1.05 |

作为对照的 FP16 累加不变，FP32 累加路径接近翻倍。寄存器回读一致：
`READOUT_1` 从 `0x410080` 变为 `0`，`SS0=0x88888888`、`SS1=0x8` 在 FLR 和
显示重连之后仍然保持。

证据：[`docs/verified-gm5ar7o.md`](docs/verified-gm5ar7o.md)、
[`docs/logs/`](docs/logs)。

## 原理

1. 从 `BAR0+0x300000` 读取这块卡自己的 VBIOS，解析 FWSEC 描述符。
2. 加载签名 GSP Falcon 固件，建立 WPR2。
3. 在 SEC2 上运行固定版本的 AD102 家族 Booter 与四 PLM payload，打开三个
   权限寄存器。
4. 写入 `SS0=0x88888888`、`SS1=0x8`，执行一次 PCIe FLR，确认选择器保持，
   重连显示驱动，启动 Windows。

## 构建

需要 Python 3、Zig 0.14.1，以及 `PATH` 中的 `zstd`。

```powershell
python scripts/make_assets.py --out assets     # 固定 NVIDIA 输入，哈希校验
python build.py --zig C:\path\to\zig.exe --out build
```

`build.py` 生成五个镜像。`--safe-only` 去掉 `UNLOCKA2820`，它是唯一无需按键
就会解锁的镜像。

| 镜像 | 写入 GPU | 需要按键 |
|---|---:|---|
| `SURVEY2820` | 否 | 否 |
| `DRYRUN2820` | 否 | 否 |
| `RELTEST2820` | 否 | `U` |
| `UNLOCKM2820` | 是 | `U` |
| `UNLOCKA2820` | 是 | 否 |

`python tools/check_reference_build.py` 会把你的构建与记录的哈希对比。当前源码
可逐字节复现全部五个镜像，包括两个实机运行过的镜像；CI 执行同样的检查。

## 使用

你需要：

- 一个可以清空的 U 盘 —— FAT32，128 MB 就够
- Secure Boot **关闭** —— 镜像未签名
- 快速启动 **关闭** —— 否则 Windows 的「关机」会跳过固件启动
- BitLocker 已挂起（如果启用了）
- 数据已备份

```powershell
python scripts/make_stick.py --build build --assets assets --out stick
# 把 stick\ 内容复制到 FAT32 U 盘根目录，然后：
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply
```

| 状态 | 结果 |
|---|---|
| 插着 U 盘冷启动 | 固件启动 U 盘，解锁，进入 Windows |
| 拔掉 U 盘冷启动 | 固件回退到 Windows Boot Manager，GPU 保持原始 |

首次启动：完全关机，等电源灯熄灭，长按电源键 10 秒，再开机并打开启动菜单
（验证机上是 F7）。

3 秒倒计时内：`Esc` 打开菜单，`S` 进入未解锁的 Windows，`U` 立即解锁。
用 `-Remove -Apply` 撤销启动项。

三种常见失败原因，按出现频率排序：

- 快速启动没关：Windows 的「关机」会跳过固件启动路径，U 盘根本不会运行。
- U 盘换了 USB 端口：记录的设备路径可能不匹配，重新执行 `-Apply`。
- 固件报「no boot device」而不回退：删掉启动项，改为每次用启动菜单选 U 盘。

睡眠唤醒、驱动重启或驱动更新都会让 GPU 回到原始状态，只有经 U 盘的冷启动能
恢复解锁。

## 验证新机器

不要跳阶段。

1. `SURVEY2820` —— 只读。把日志发来审阅。
2. `DRYRUN2820` —— 仅精确目标，不写入。应看到 `Checks passed.`
3. `RELTEST2820` —— 按 `U`。应看到 `release test: status=0 gop=1`。
4. `UNLOCKM2820` —— 按 `U`。应看到 `TRANSACTION OK`。

```powershell
python scripts/make_stick.py --layout staged --out stick
```

## 失败时

在第一个失败的阶段停下。写入之前失败，程序记录原因并进入未解锁的 Windows；
写入之后失败，程序只做 containment 然后停机。

如果屏幕显示 `STOPPED`，或真实事务后约两分钟仍未进入 Windows：长按电源键直到
断电，拔掉 U 盘，启动 Windows Boot Manager。完全断电即恢复原状。

## 仓库结构

```text
target_2820.h                  精确写入目标
build.py                       构建（--safe-only 去掉自动镜像）
scripts/make_assets.py         从固定 NVIDIA 输入生成固件资产
scripts/make_stick.py          即插即用或分阶段 U 盘布局
scripts/usb_boot_entry.ps1     可撤销的固件启动项
tools/check_reference_build.py 构建与记录哈希的对比
vendor/, compat/               事务核心与 UEFI 兼容层
tests/                         模拟 PCI/MMIO/DMA/失败场景测试
docs/                          报告、日志、参考哈希
```

## 许可与来源

GPL-2.0-only。许可与上游声明见 `LICENSE*`、`THIRD_PARTY_NOTICES.md`、
`NVIDIA-FILES.md`、`provenance.json`。基于 `JustAResearcher/gpu-unlock-ada`、
`MarvinFS/rtx4090-uefi`、`NekoMirra/rtx4060-laptop-tensor-unlock` 和
`Zagitta/gpu-unlock`。NVIDIA 固件在本地下载，不随仓库分发。

## 免责声明

实验性研究代码，仅在一款笔记本上验证，不提供任何担保。它可能导致黑屏、启动
失败、驱动异常或数据丢失。运行它的人是你，责任也在你。
