"""已安装软件管理与残留扫描（参考 Geek Uninstaller 的做法）。

只读枚举 + 由用户确认后执行卸载/清理，不做任何自动化静默删除。
"""
from __future__ import annotations

import ctypes
import os
import re
import subprocess
import winreg
from dataclasses import dataclass, field
from pathlib import Path

UNINSTALL_KEYS = [
    ("HKLM64", winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
    ("HKLM32", winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
    ("HKCU", winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
]

# 仅作为提示，不代表一定是流氓软件；命中会在界面标记「疑似捆绑」，由用户判断
BUNDLE_HINTS = [
    "全家桶", "助手", "加速器", "清理大师", "优化大师", "壁纸", "天气", "导航",
    "游戏盒子", "桌面日历", "抢票", "看图", "输入法", "浏览器", "影视", "播放器",
    "装机", "快装", "装机助手", "软件管家", "安全卫士", "杀毒", "驱动人生",
    "驱动精灵", "鲁大师", "2345", "hao123", "快压", "WPS 图片", "桌面整理",
]


@dataclass
class InstalledApp:
    key: str                     # 注册表完整路径
    hive: str                    # HKLM64 / HKLM32 / HKCU
    name: str
    publisher: str = ""
    version: str = ""
    install_date: str = ""
    size_kb: int = 0
    install_location: str = ""
    uninstall_string: str = ""
    quiet_uninstall: str = ""
    display_icon: str = ""
    url: str = ""

    @property
    def hive_root(self):
        return {
            "HKLM64": winreg.HKEY_LOCAL_MACHINE,
            "HKLM32": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }[self.hive]

    @property
    def subkey(self) -> str:
        return self.key

    @property
    def needs_admin(self) -> bool:
        return self.hive.startswith("HKLM")

    def size_text(self) -> str:
        if not self.size_kb:
            return "-"
        n = float(self.size_kb) * 1024
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
            n /= 1024
        return "-"

    def date_text(self) -> str:
        d = self.install_date.strip()
        if len(d) == 8 and d.isdigit():
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
        return d or "-"

    def suspicious(self) -> tuple[bool, str]:
        """返回 (是否疑似, 原因)。仅作提示。"""
        reasons = []
        if not self.uninstall_string.strip():
            reasons.append("无卸载程序")
        if not self.publisher.strip():
            reasons.append("无发布者信息")
        if self.install_location and not os.path.isdir(
                os.path.expandvars(self.install_location)):
            reasons.append("安装目录已不存在")
        low = self.name.lower()
        for word in BUNDLE_HINTS:
            if word.lower() in low:
                reasons.append(f"名称含「{word}」")
                break
        return bool(reasons), "、".join(reasons)


def _read_values(root, subkey: str, flags: int) -> dict:
    out: dict = {}
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | flags) as h:
            i = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(h, i)
                except OSError:
                    break
                out[name] = value
                i += 1
    except OSError:
        pass
    return out


def _subkeys(root, subkey: str, flags: int) -> list[str]:
    out: list[str] = []
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | flags) as h:
            i = 0
            while True:
                try:
                    out.append(winreg.EnumKey(h, i))
                except OSError:
                    break
                i += 1
    except OSError:
        pass
    return out


def list_installed() -> list[InstalledApp]:
    apps: list[InstalledApp] = []
    seen: set[str] = set()
    for tag, root, base, flags in UNINSTALL_KEYS:
        for name in _subkeys(root, base, flags):
            full = base + "\\" + name
            vals = _read_values(root, full, flags)
            display = str(vals.get("DisplayName") or "").strip()
            if not display:
                continue
            if str(vals.get("SystemComponent") or "") == "1":
                continue
            if vals.get("ParentKeyName"):
                continue
            if str(vals.get("ReleaseType") or "").lower() in ("update", "hotfix"):
                continue
            dedup = f"{display}|{vals.get('DisplayVersion','')}|{tag}"
            if dedup in seen:
                continue
            seen.add(dedup)
            try:
                size = int(vals.get("EstimatedSize") or 0)
            except (TypeError, ValueError):
                size = 0
            apps.append(InstalledApp(
                key=full,
                hive=tag,
                name=display,
                publisher=str(vals.get("Publisher") or "").strip(),
                version=str(vals.get("DisplayVersion") or "").strip(),
                install_date=str(vals.get("InstallDate") or "").strip(),
                size_kb=size,
                install_location=str(vals.get("InstallLocation") or "").strip(),
                uninstall_string=str(vals.get("UninstallString") or "").strip(),
                quiet_uninstall=str(vals.get("QuietUninstallString") or "").strip(),
                display_icon=str(vals.get("DisplayIcon") or "").strip(),
                url=str(vals.get("URLInfoAbout") or "").strip(),
            ))
    apps.sort(key=lambda a: a.name.lower())
    return apps


def backup_registry(subkey_path: str, hive_tag: str, tag: str = "uninstall") -> str:
    """导出注册表键做备份。"""
    from .paths import BACKUP_DIR
    from datetime import datetime
    HIVE = {"HKLM64": "HKLM", "HKLM32": "HKLM", "HKCU": "HKCU"}
    hive = HIVE.get(hive_tag, "HKLM")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"{tag}_{datetime.now():%Y%m%d_%H%M%S}.reg"
    try:
        proc = subprocess.run(
            ["reg", "export", f"{hive}\\{subkey_path}", str(dest), "/y"],
            capture_output=True, text=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return str(dest) if proc.returncode == 0 and dest.exists() else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------- 执行卸载
def _split_command(cmd: str) -> tuple[str, str]:
    cmd = cmd.strip()
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end > 0:
            return cmd[1:end], cmd[end + 1:].strip()
    for token in (" /", " -"):
        idx = cmd.find(token)
        if idx > 0:
            return cmd[:idx].strip(), cmd[idx + 1:].strip()
    return cmd, ""


def launch_uninstaller(app: InstalledApp, silent: bool = False) -> tuple[bool, str]:
    """调用软件自带卸载程序；需要管理员时会弹 UAC。"""
    cmd = (app.quiet_uninstall if silent and app.quiet_uninstall else "") or app.uninstall_string
    if not cmd:
        return False, "该软件没有提供卸载程序，请使用「强制移除」"
    exe, params = _split_command(cmd)
    exe = os.path.expandvars(exe)
    if not os.path.exists(exe):
        # 可能是 MSI 或系统组件
        if "msiexec" in cmd.lower():
            exe, params = "msiexec.exe", params
        else:
            return False, f"卸载程序不存在：{exe}"
    try:
        verb = "runas" if app.needs_admin else "open"
        ret = ctypes.windll.shell32.ShellExecuteW(None, verb, exe, params or None, None, 1)
        if ret <= 32:
            return False, f"启动卸载程序失败（代码 {ret}）"
        return True, "已启动卸载程序，请按提示完成卸载"
    except Exception as exc:
        return False, f"启动卸载程序失败：{exc}"


def remove_uninstall_entry(app: InstalledApp) -> tuple[bool, str]:
    """强制移除注册表中的卸载记录（会先备份）。"""
    backup = backup_registry(app.key, app.hive, "uninstall_entry")
    try:
        with winreg.OpenKey(app.hive_root, app.key.rsplit("\\", 1)[0], 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as h:
            winreg.DeleteKey(h, app.key.rsplit("\\", 1)[1])
        note = f"已移除卸载记录" + (f"（已备份 {os.path.basename(backup)}）" if backup else "")
        return True, note
    except OSError as exc:
        return False, f"移除失败：{exc}"


# ---------------------------------------------------------------------------- 残留扫描
def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(v?\d+(\.\d+)+)\b", "", text)     # 版本号
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)
    return text


def _scan_roots() -> list[Path]:
    roots: list[Path] = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "ProgramData",
                "LOCALAPPDATA", "APPDATA"):
        value = os.environ.get(env)
        if value:
            roots.append(Path(value))
    return [r for r in roots if r.is_dir()]


@dataclass
class Leftover:
    kind: str          # file / registry
    path: str
    size: int = 0
    detail: str = ""
    hive: str = ""

    def size_text(self) -> str:
        if self.kind == "registry":
            return "-"
        n = float(self.size or 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
            n /= 1024
        return "-"


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for root, dirs, files in os.walk(path, onerror=lambda e: None, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for name in files:
                fp = os.path.join(root, name)
                if os.path.islink(fp):
                    continue
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    continue
    except Exception:
        pass
    return total


def scan_leftovers(app: InstalledApp) -> list[Leftover]:
    """扫描该软件的残留目录与注册表项。只扫描固定根目录，不会越界。"""
    found: list[Leftover] = []
    tokens = {_normalize(app.name), _normalize(app.publisher)}
    tokens = {t for t in tokens if len(t) >= 4}
    if not tokens:
        return found

    # 1) 安装目录本身
    if app.install_location:
        loc = Path(os.path.expandvars(app.install_location))
        if loc.is_dir():
            found.append(Leftover("file", str(loc), _dir_size(loc), "安装目录"))
        elif loc.exists():
            found.append(Leftover("file", str(loc), 0, "安装路径"))

    # 2) 常见目录下的同名文件夹
    for root in _scan_roots():
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            try:
                if not child.is_dir() or child.is_symlink():
                    continue
            except OSError:
                continue
            norm = _normalize(child.name)
            if len(norm) < 4:
                continue
            if any(t and (t in norm or norm in t) for t in tokens):
                if any(os.path.normcase(str(child)) == os.path.normcase(f.path) for f in found):
                    continue
                found.append(Leftover("file", str(child), _dir_size(child), f"位于 {root.name}"))

    # 3) 注册表残留
    for hive_tag, root, base, flags in UNINSTALL_KEYS:
        for name in _subkeys(root, base, flags):
            full = base + "\\" + name
            vals = _read_values(root, full, flags)
            display = str(vals.get("DisplayName") or "").strip()
            if display and _normalize(display) in tokens:
                if full == app.key:
                    continue
                found.append(Leftover("registry", full, 0, f"卸载记录：{display}", hive_tag))

    for hive_tag, root, base, flags in (
        ("HKLM64", winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE", winreg.KEY_WOW64_64KEY),
        ("HKLM32", winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node", winreg.KEY_WOW64_64KEY),
        ("HKCU", winreg.HKEY_CURRENT_USER, r"SOFTWARE", winreg.KEY_WOW64_64KEY),
    ):
        for name in _subkeys(root, base, flags):
            norm = _normalize(name)
            if norm and norm in tokens:
                found.append(Leftover("registry", base + "\\" + name, 0,
                                      f"软件注册表项：{name}", hive_tag))
    return found


def delete_leftover(item: Leftover) -> tuple[bool, str]:
    if item.kind == "registry":
        backup = backup_registry(item.path, item.hive or "HKLM64", "leftover")
        parent, _, leaf = item.path.rpartition("\\")
        root = winreg.HKEY_CURRENT_USER if (item.hive or "").startswith("HKCU") else winreg.HKEY_LOCAL_MACHINE
        try:
            with winreg.OpenKey(root, parent, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as h:
                winreg.DeleteKey(h, leaf)
            return True, "已删除注册表项"
        except OSError as exc:
            return False, f"删除失败：{exc}"
    path = Path(item.path)
    if not path.exists():
        return True, "目录已不存在"
    try:
        import shutil
        shutil.rmtree(path, ignore_errors=False)
        return True, "已删除"
    except PermissionError as exc:
        return False, f"文件被占用或无权限：{exc}"
    except OSError as exc:
        return False, f"删除失败：{exc}"
