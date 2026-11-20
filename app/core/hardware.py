"""硬件信息采集（只读）。

优先用 PowerShell CIM 一次性取回 JSON；CIM 不可用时回退到注册表 / Win32 API。
不使用 wmic —— 它已在 Windows 11 24H2 起被移除。
Windows 10 1709+ / Windows 11 全版本可用。
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import socket
import subprocess
import winreg
from dataclasses import dataclass, field

PS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function S($v) { if ($null -eq $v) { '' } else { "$v".Trim() } }

$cs   = Get-CimInstance -ClassName Win32_ComputerSystem
$cpu  = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
$bb   = Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -First 1
$bios = Get-CimInstance -ClassName Win32_BIOS | Select-Object -First 1
$os   = Get-CimInstance -ClassName Win32_OperatingSystem

$mem = @()
foreach ($m in (Get-CimInstance -ClassName Win32_PhysicalMemory)) {
  $mem += [pscustomobject]@{
    slot = S $m.DeviceLocator; size = [int64]$m.Capacity; speed = [int]$m.Speed
    configured = [int]$m.ConfiguredClockSpeed; maker = S $m.Manufacturer
    part = S $m.PartNumber; serial = S $m.SerialNumber
    type = [int]$m.SMBIOSMemoryType; form = [int]$m.FormFactor
  }
}

$gpu = @()
foreach ($g in (Get-CimInstance -ClassName Win32_VideoController)) {
  $gpu += [pscustomobject]@{
    name = S $g.Name; ram = [int64]$g.AdapterRAM; driver = S $g.DriverVersion
    drvdate = S $g.DriverDate; id = S $g.PNPDeviceID
    width = [int]$g.CurrentHorizontalResolution; height = [int]$g.CurrentVerticalResolution
    vram_reg = [int64]0
  }
}

$disk = @()
foreach ($d in (Get-PhysicalDisk)) {
  $disk += [pscustomobject]@{
    model = S $d.FriendlyName; serial = S $d.SerialNumber; size = [int64]$d.Size
    media = S $d.MediaType; bus = S $d.BusType; health = S $d.HealthStatus
    spindle = [int]$d.SpindleSpeed
  }
}
if ($disk.Count -eq 0) {
  foreach ($d in (Get-CimInstance -ClassName Win32_DiskDrive)) {
    $disk += [pscustomobject]@{
      model = S $d.Model; serial = S $d.SerialNumber; size = [int64]$d.Size
      media = S $d.MediaType; bus = S $d.InterfaceType; health = ''; spindle = [int]
    }
  }
}

$net = @()
foreach ($n in (Get-CimInstance -ClassName Win32_NetworkAdapter -Filter 'PhysicalAdapter=True')) {
  if (-not $n.MACAddress) { continue }
  $net += [pscustomobject]@{
    name = S $n.Name; mac = S $n.MACAddress; speed = [int64]$n.Speed; id = S $n.PNPDeviceID
  }
}

[pscustomobject]@{
  ok = $true
  computer = [pscustomobject]@{
    name = S $cs.Name; maker = S $cs.Manufacturer; model = S $cs.Model
    total_mem = [int64]$cs.TotalPhysicalMemory; user = S $cs.UserName
    domain = S $cs.Domain
  }
  cpu = [pscustomobject]@{
    name = S $cpu.Name; cores = [int]$cpu.NumberOfCores
    threads = [int]$cpu.NumberOfLogicalProcessors; max_clock = [int]$cpu.MaxClockSpeed
    socket = S $cpu.SocketDesignation; id = S $cpu.ProcessorId; maker = S $cpu.Manufacturer
    l2 = [int]$cpu.L2CacheSize; l3 = [int]$cpu.L3CacheSize
  }
  board = [pscustomobject]@{
    maker = S $bb.Manufacturer; product = S $bb.Product
    version = S $bb.Version; serial = S $bb.SerialNumber
  }
  bios = [pscustomobject]@{
    vendor = S $bios.Manufacturer; version = S $bios.SMBIOSBIOSVersion
    full_version = S $bios.Version
    date = S $bios.ReleaseDate; serial = S $bios.SerialNumber
  }
  os = [pscustomobject]@{
    caption = S $os.Caption; version = S $os.Version; build = S $os.BuildNumber
    arch = S $os.OSArchitecture; install = S $os.InstallDate
    boot = S $os.LastBootUpTime
  }
  memory = $mem; gpu = $gpu; disk = $disk; net = $net
} | ConvertTo-Json -Depth 6 -Compress
"""


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return value
    return []


def _run_ps(script: str, timeout: int = 45) -> str:
    si = None
    flags = 0
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        flags = subprocess.CREATE_NO_WINDOW
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", script],
        capture_output=True, timeout=timeout, startupinfo=si, creationflags=flags,
    )
    return proc.stdout.decode("utf-8", "ignore").strip()


# ---------------------------------------------------------------------------- 注册表回退
def _reg(path: str, name: str, hive=winreg.HKEY_LOCAL_MACHINE) -> str:
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as h:
            value, _kind = winreg.QueryValueEx(h, name)
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")
            return str(value).strip()
    except OSError:
        return ""


def _volume_serial(drive: str = "C:\\") -> str:
    try:
        serial = ctypes.c_ulong(0)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive), None, 0, ctypes.byref(serial), None, None, None, 0,
        )
        return f"{serial.value:08X}"
    except Exception:
        return ""


def _fallback() -> dict:
    """PowerShell/CIM 不可用时的最小信息集。"""
    cpu_name = _reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
    bios = {
        "vendor": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "BIOSVendor"),
        "version": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "BIOSVersion"),
        "date": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "BIOSReleaseDate"),
        "serial": "",
    }
    board = {
        "maker": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "BaseBoardManufacturer"),
        "product": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "BaseBoardProduct"),
        "version": "",
        "serial": "",
    }
    return {
        "ok": False,
        "degraded": True,
        "computer": {
            "name": socket.gethostname(),
            "maker": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "SystemManufacturer"),
            "model": _reg(r"HARDWARE\DESCRIPTION\System\BIOS", "SystemProductName"),
            "total_mem": 0,
            "user": os.environ.get("USERNAME", ""),
            "domain": "",
        },
        "cpu": {"name": cpu_name, "cores": 0, "threads": os.cpu_count() or 0,
                "max_clock": 0, "socket": "", "id": "", "maker": "", "l2": 0, "l3": 0},
        "board": board,
        "bios": bios,
        "os": {"caption": f"{platform.system()} {platform.release()}",
               "version": platform.version(), "build": platform.version().split(".")[-1],
               "arch": platform.machine(), "install": "", "boot": ""},
        "memory": [], "gpu": [], "net": [],
        "disk": [{"model": "系统盘 C:", "serial": _volume_serial(),
                  "size": 0, "media": "", "bus": "", "health": "", "spindle": 0}],
    }


def collect() -> dict:
    """采集硬件信息。任何失败都会回退，不会抛异常。"""
    try:
        text = _run_ps(PS_SCRIPT)
    except Exception:
        text = ""
    data = None
    if text:
        start = text.find("{")
        if start >= 0:
            try:
                data = json.loads(text[start:])
            except Exception:
                data = None
    if not isinstance(data, dict):
        data = _fallback()
    for key in ("memory", "gpu", "disk", "net"):
        data[key] = _as_list(data.get(key))
    data["vram_map"] = _vram_from_registry()
    data["platform"] = f"{platform.system()} {platform.release()}"
    return data


_GPU_CLASS = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"


def _vram_from_registry() -> list[dict]:
    """WMI 的 AdapterRAM 是 32 位，超过 4GB 会溢出；注册表里的 qwMemorySize 才是准的。"""
    out: list[dict] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _GPU_CLASS, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as root:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                if not name.isdigit():
                    continue
                sub = _GPU_CLASS + "\\" + name
                desc = _reg(sub, "DriverDesc")
                size = 0
                for value_name in ("HardwareInformation.qwMemorySize",
                                   "HardwareInformation.MemorySize"):
                    raw = _reg_raw(sub, value_name)
                    if isinstance(raw, int) and raw > size:
                        size = raw
                if size:
                    out.append({"desc": desc, "bytes": int(size)})
    except OSError:
        pass
    return out


def _reg_raw(path: str, name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as h:
            return winreg.QueryValueEx(h, name)[0]
    except OSError:
        return None


def match_vram(name: str, fallback_mb: int, vram_map: list[dict]) -> int:
    """返回显存字节数，优先用注册表精确值。"""
    if name:
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        for item in vram_map:
            desc = "".join(ch for ch in str(item.get("desc", "")).lower() if ch.isalnum())
            if not desc:
                continue
            if desc in key or key in desc:
                return int(item["bytes"])
    if len(vram_map) == 1:
        return int(vram_map[0]["bytes"])
    return int(fallback_mb or 0) * 1024 * 1024


# ---------------------------------------------------------------------------- 人类可读
MEM_TYPE = {
    20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5",
    0: "", 1: "Other", 2: "Unknown",
}
MEM_FORM = {8: "DIMM", 12: "SODIMM", 13: "SRIMM", 0: "Unknown"}


def fmt_bytes(value) -> str:
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "-"
    if n <= 0:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return "-"


@dataclass
class HwField:
    label: str
    value: str
    mono: bool = False


@dataclass
class HwSection:
    key: str
    title: str
    icon: str = ""
    fields: list[HwField] = field(default_factory=list)
    entries: list[tuple[str, list[HwField]]] = field(default_factory=list)


def build_sections(data: dict) -> list[HwSection]:
    """把原始数据整理成界面用的分区。"""
    sections: list[HwSection] = []
    g = lambda d, k, dflt="": (d or {}).get(k, dflt) or dflt  # noqa: E731

    def placeholder(value: str) -> bool:
        """部分整机/准系统厂商会在 SMBIOS 里填纯数字占位串。"""
        text = str(value or "").strip()
        return len(text) >= 8 and text.isdigit()

    cpu = data.get("cpu") or {}
    clock = int(cpu.get("max_clock") or 0)
    cpu_fields = [
        HwField("型号", g(cpu, "name") or "-"),
        HwField("厂商", g(cpu, "maker") or "-"),
        HwField("核心 / 线程", f"{cpu.get('cores') or '-'} 核 / {cpu.get('threads') or '-'} 线程"),
        HwField("主频", f"{clock / 1000:.2f} GHz" if clock else "-"),
    ]
    if cpu.get("socket"):
        cpu_fields.append(HwField("插槽", g(cpu, "socket")))
    if cpu.get("l3"):
        cpu_fields.append(HwField("三级缓存", f"{int(cpu['l3']) / 1024:.1f} MB"))
    if cpu.get("id"):
        cpu_fields.append(HwField("处理器 ID", g(cpu, "id"), mono=True))
    sections.append(HwSection("cpu", "处理器", "CPU", cpu_fields))

    board = data.get("board") or {}
    bios = data.get("bios") or {}
    bios_version = g(bios, "version")
    if placeholder(bios_version):
        bios_version = g(bios, "full_version") or bios_version
    board_maker = g(board, "maker")
    board_maker = "" if placeholder(board_maker) else board_maker
    board_fields = [
        HwField("主板型号", f"{board_maker} {g(board, 'product')}".strip() or "-"),
        HwField("主板序列号", g(board, "serial") or "-", mono=True),
        HwField("BIOS 版本", bios_version or "-"),
    ]
    bios_vendor = g(bios, "vendor")
    if bios_vendor and not placeholder(bios_vendor):
        board_fields.append(HwField("BIOS 厂商", bios_vendor))
    if bios.get("date"):
        board_fields.append(HwField("BIOS 日期", str(bios["date"])[:10]))
    if bios.get("serial"):
        board_fields.append(HwField("BIOS 序列号", g(bios, "serial"), mono=True))
    sections.append(HwSection("board", "主板与 BIOS", "BOARD", board_fields))

    memory = data.get("memory") or []
    total = sum(int(m.get("size") or 0) for m in memory)
    entries = []
    for i, m in enumerate(memory, start=1):
        speed = m.get("configured") or m.get("speed") or 0
        mem_fields = [
            HwField("容量", fmt_bytes(m.get("size"))),
            HwField("频率", f"{speed} MHz" if speed else "-"),
            HwField("类型", MEM_TYPE.get(int(m.get("type") or 0), "") or "-"),
        ]
        if m.get("maker"):
            mem_fields.append(HwField("厂商", str(m["maker"]).strip()))
        if m.get("part"):
            mem_fields.append(HwField("型号", str(m["part"]).strip()))
        if m.get("serial"):
            mem_fields.append(HwField("序列号", str(m["serial"]).strip(), mono=True))
        entries.append((f"内存条 {i}　{g(m, 'slot') or ''}".strip(), mem_fields))
    sections.append(HwSection(
        "memory", "内存", "RAM",
        [HwField("总容量", fmt_bytes(total) if total else "-"),
         HwField("内存条数量", f"{len(memory)} 条" if memory else "-")],
        entries,
    ))

    gpu = data.get("gpu") or []
    entries = []
    vram_map = data.get("vram_map") or []
    for i, item in enumerate(gpu, start=1):
        name = g(item, "name") or "-"
        vram = match_vram(name, int(item.get("ram") or 0) // (1024 * 1024), vram_map)
        fields = [HwField("显存", fmt_bytes(vram) if vram else "-")]
        if item.get("driver"):
            fields.append(HwField("驱动版本", g(item, "driver"), mono=True))
        if item.get("drvdate"):
            fields.append(HwField("驱动日期", str(item["drvdate"])[:10]))
        if item.get("width") and item.get("height"):
            fields.append(HwField("当前分辨率", f"{item['width']} × {item['height']}"))
        if item.get("id"):
            fields.append(HwField("设备 ID", g(item, "id"), mono=True))
        entries.append((name, fields))
    sections.append(HwSection("gpu", "显卡", "GPU",
                              [HwField("显卡数量", f"{len(gpu)} 个" if gpu else "-")], entries))

    disk = data.get("disk") or []
    entries = []
    for i, d in enumerate(disk, start=1):
        fields = [HwField("容量", fmt_bytes(d.get("size")))]
        if d.get("media"):
            fields.append(HwField("类型", str(d["media"])))
        if d.get("bus"):
            fields.append(HwField("接口", str(d["bus"])))
        if d.get("health"):
            fields.append(HwField("健康状态", str(d["health"])))
        fields.append(HwField("序列号", g(d, "serial") or "-", mono=True))
        entries.append((g(d, "model") or f"磁盘 {i}", fields))
    sections.append(HwSection("disk", "硬盘", "DISK",
                              [HwField("硬盘数量", f"{len(disk)} 块" if disk else "-")], entries))

    net = data.get("net") or []
    entries = []
    for n in net:
        fields = [HwField("MAC 地址", g(n, "mac") or "-", mono=True)]
        speed = int(n.get("speed") or 0)
        if speed > 0:
            fields.append(HwField("连接速率", f"{speed / 1_000_000:.0f} Mbps"))
        entries.append((g(n, "name") or "网卡", fields))
    if net:
        sections.append(HwSection("net", "网卡", "NET", [], entries))

    comp = data.get("computer") or {}
    osinfo = data.get("os") or {}
    sys_fields = [
        HwField("计算机名", g(comp, "name") or "-"),
        HwField("产品名称", g(comp, "model") or g(board, "product") or "-"),
        HwField("品牌型号", f"{g(comp, 'maker')} {g(comp, 'model')}".strip() or "-"),
        HwField("操作系统", g(osinfo, "caption") or data.get("platform", "-")),
        HwField("系统版本", f"{g(osinfo, 'version')} (Build {g(osinfo, 'build')})".strip()),
        HwField("系统架构", g(osinfo, "arch") or "-"),
        HwField("可用物理内存", fmt_bytes(comp.get("total_mem"))),
    ]
    if comp.get("user"):
        sys_fields.append(HwField("当前用户", g(comp, "user")))
    sections.append(HwSection("system", "系统", "SYS", sys_fields))
    return sections
