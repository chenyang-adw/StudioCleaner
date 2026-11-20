"""可清理项注册表。

只包含内容/隐私/系统维护类项目：
临时文件、缓存、日志、网络残留、卸载残留、无效启动项。
不涉及任何设备身份（显示器 EDID/序列号、显卡 UUID、设备枚举历史）的改写或擦除。
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import sqlite3
import subprocess
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .admin import is_admin
from .paths import BACKUP_DIR, roaming_appdata, user_temp_dirs, windows_dir
from .sizes import dir_stats

RISK_SAFE = "safe"
RISK_NORMAL = "normal"
RISK_HIGH = "high"

CATEGORIES = ["系统缓存", "浏览器", "网络", "系统维护"]

LogFn = Callable[[str], None]


def _noop(_msg: str) -> None:
    pass


@dataclass(frozen=True)
class CleanItem:
    key: str
    label: str
    desc: str
    category: str
    risk: str
    requires_admin: bool
    default_selected: bool
    scan: Callable[[], tuple[int, int]]
    clean: Callable[[LogFn], dict]
    blocked_by: tuple[str, ...] = ()


# --------------------------------------------------------------------------------------
# 安全边界：只允许删除白名单根目录内部的内容
# --------------------------------------------------------------------------------------
def _allowed_roots() -> list[str]:
    roots = [str(p) for p in user_temp_dirs()]
    roots.append(str(windows_dir() / "Temp"))
    roots.append(str(windows_dir() / "SoftwareDistribution" / "Download"))
    roots.append(str(windows_dir().parent / "Windows.old"))
    la = os.environ.get("LOCALAPPDATA")
    if la:
        roots += [
            str(Path(la) / "Microsoft" / "Windows" / "INetCache"),
            str(Path(la) / "Microsoft" / "Windows" / "WER"),
            str(Path(la) / "CrashDumps"),
            str(Path(la) / "Microsoft" / "Windows" / "Explorer"),
            str(Path(la) / "Google" / "Chrome" / "User Data"),
            str(Path(la) / "Microsoft" / "Edge" / "User Data"),
            str(Path(la) / "Mozilla" / "Firefox" / "Profiles"),
        ]
    ra = os.environ.get("APPDATA")
    if ra:
        roots.append(str(Path(ra) / "Microsoft" / "Windows" / "INetCache"))
    home = os.environ.get("USERPROFILE")
    if home:
        roots.append(str(Path(home) / "Downloads"))
    return [os.path.normcase(os.path.normpath(r)) for r in roots]


def _is_allowed(path) -> bool:
    p = os.path.normcase(os.path.normpath(str(path)))
    for root in _allowed_roots():
        if p == root or p.startswith(root + os.sep):
            return True
    return False


class _Counter:
    def __init__(self) -> None:
        self.removed = 0
        self.freed = 0
        self.skipped = 0

    def result(self, note: str = "") -> dict:
        return {
            "removed": self.removed,
            "freed": self.freed,
            "skipped": self.skipped,
            "note": note,
        }


def _rm_file(fp: str, c: _Counter) -> None:
    try:
        size = os.path.getsize(fp)
    except OSError:
        size = 0
    try:
        os.remove(fp)
        c.removed += 1
        c.freed += size
    except (PermissionError, OSError):
        c.skipped += 1


def _clean_dir(path, log: LogFn = _noop, c: _Counter | None = None) -> _Counter:
    """删除目录内部的全部内容，保留目录本身。"""
    c = c or _Counter()
    root = Path(path)
    if not _is_allowed(root):
        log(f"跳过（不在允许范围）: {root}")
        return c
    if not root.is_dir():
        return c
    try:
        entries = list(os.scandir(root))
    except OSError:
        c.skipped += 1
        return c
    for entry in entries:
        try:
            if entry.is_symlink():
                c.skipped += 1
                continue
            if entry.is_dir(follow_symlinks=False):
                _files, size = dir_stats(entry.path)
                try:
                    shutil.rmtree(entry.path, ignore_errors=False)
                    c.removed += 1
                    c.freed += size
                except (PermissionError, OSError):
                    c.skipped += 1
            else:
                _rm_file(entry.path, c)
        except OSError:
            c.skipped += 1
    return c


def _clean_glob(patterns: list[str], log: LogFn = _noop) -> _Counter:
    c = _Counter()
    for pattern in patterns:
        for fp in glob.glob(pattern):
            if not _is_allowed(fp) or os.path.islink(fp):
                c.skipped += 1
                continue
            if os.path.isdir(fp):
                _files, size = dir_stats(fp)
                try:
                    shutil.rmtree(fp, ignore_errors=False)
                    c.removed += 1
                    c.freed += size
                except (PermissionError, OSError):
                    c.skipped += 1
            else:
                _rm_file(fp, c)
    return c


def _stats_all(patterns: list[str]) -> tuple[int, int]:
    files = 0
    total = 0
    for pattern in patterns:
        for fp in glob.glob(pattern):
            f, b = dir_stats(fp)
            files += f
            total += b
    return files, total


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    si = None
    flags = 0
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        flags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        cmd, capture_output=True, text=True, shell=False,
        startupinfo=si, creationflags=flags, timeout=timeout,
        errors="ignore",
    )


# --------------------------------------------------------------------------------------
# 系统缓存
# --------------------------------------------------------------------------------------
def _scan_temp_user() -> tuple[int, int]:
    files = total = 0
    for p in user_temp_dirs():
        f, b = dir_stats(p)
        files += f
        total += b
    return files, total


def _clean_temp_user(log: LogFn) -> dict:
    c = _Counter()
    seen: set[str] = set()
    for p in user_temp_dirs():
        key = os.path.normcase(os.path.normpath(str(p)))
        if key in seen:
            continue
        seen.add(key)
        log(f"清理临时目录: {p}")
        _clean_dir(p, log, c)
    return c.result()


def _scan_temp_system() -> tuple[int, int]:
    return dir_stats(windows_dir() / "Temp")


def _clean_temp_system(log: LogFn) -> dict:
    log(f"清理系统临时目录: {windows_dir() / 'Temp'}")
    return _clean_dir(windows_dir() / "Temp", log).result()


def _wer_patterns() -> list[str]:
    la = os.environ.get("LOCALAPPDATA", "")
    if not la:
        return []
    base = os.path.join(la, "Microsoft", "Windows", "WER")
    return [
        os.path.join(la, "CrashDumps", "*"),
        os.path.join(base, "ReportQueue", "*"),
        os.path.join(base, "ReportArchive", "*"),
        os.path.join(base, "Temp", "*"),
    ]


def _scan_crash_dumps() -> tuple[int, int]:
    return _stats_all(_wer_patterns())


def _clean_crash_dumps(log: LogFn) -> dict:
    la = os.environ.get("LOCALAPPDATA", "")
    c = _Counter()
    for name in ("CrashDumps",):
        if la:
            log(f"清理崩溃转储: {name}")
            _clean_dir(Path(la) / name, log, c)
    if la:
        base = Path(la) / "Microsoft" / "Windows" / "WER"
        for name in ("ReportQueue", "ReportArchive", "Temp"):
            _clean_dir(base / name, log, c)
    return c.result()


def _thumb_patterns() -> list[str]:
    la = os.environ.get("LOCALAPPDATA", "")
    if not la:
        return []
    d = os.path.join(la, "Microsoft", "Windows", "Explorer")
    return [
        os.path.join(d, "thumbcache_*.db"),
        os.path.join(d, "iconcache_*.db"),
    ]


def _scan_thumb_cache() -> tuple[int, int]:
    return _stats_all(_thumb_patterns())


def _clean_thumb_cache(log: LogFn) -> dict:
    log("清理缩略图与图标缓存（被资源管理器占用的文件会自动跳过）")
    return _clean_glob(_thumb_patterns(), log).result()


def _recycle_bin_scan() -> tuple[int, int]:
    """通过资源管理器回收站目录估算体积。"""
    total = 0
    files = 0
    for drive in "CDEFGH":
        p = Path(f"{drive}:\\$Recycle.Bin")
        if p.is_dir():
            f, b = dir_stats(p)
            files += f
            total += b
    return files, total


def _clean_recycle_bin(log: LogFn) -> dict:
    files, total = _recycle_bin_scan()
    if files == 0:
        log("回收站已经是空的")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": "回收站为空"}
    try:
        import ctypes
        from ctypes import wintypes

        flags = 0x1 | 0x2 | 0x4  # NOCONFIRMATION | NOPROGRESSUI | NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        if res == 0:
            log(f"回收站已清空，释放约 {total / 1048576:.2f} MB")
            return {"removed": files, "freed": total, "skipped": 0, "note": ""}
        log(f"回收站清理返回码: {res}")
        return {"removed": 0, "freed": 0, "skipped": files, "note": f"返回码 {res}"}
    except Exception as exc:  # pragma: no cover
        return {"removed": 0, "freed": 0, "skipped": files, "note": str(exc)}


# --------------------------------------------------------------------------------------
# 浏览器
# --------------------------------------------------------------------------------------
_CHROMIUM_SUBDIRS = [
    "Cache", "Code Cache", "GPUCache", "DawnCache", "GrShaderCache",
    "Service Worker/CacheStorage", "Service Worker/ScriptCache",
    "ShaderCache",
]


def _chromium_profile_dirs(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.is_dir():
        return out
    for child in root.iterdir():
        try:
            if not child.is_dir():
                continue
        except OSError:
            continue
        if child.name in ("Default", "Guest Profile", "System Profile") or child.name.startswith("Profile "):
            out.append(child)
    return out


def _chromium_cache_paths(root: Path) -> list[str]:
    out: list[str] = []
    for prof in _chromium_profile_dirs(root):
        for sub in _CHROMIUM_SUBDIRS:
            out.append(str(prof / sub.replace("/", os.sep)))
    return out


def _chrome_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"


def _edge_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"


def _scan_dirs(paths: list[Path]) -> tuple[int, int]:
    files = total = 0
    for p in paths:
        f, b = dir_stats(p)
        files += f
        total += b
    return files, total


def _clean_dirs(paths: list[Path], log: LogFn) -> dict:
    c = _Counter()
    for p in paths:
        _clean_dir(p, log, c)
    return c.result()


def _firefox_profile_dirs() -> list[Path]:
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def _firefox_cache_paths() -> list[Path]:
    out: list[Path] = []
    for prof in _firefox_profile_dirs():
        out += [prof / "cache2", prof / "startupCache", prof / "shader-cache"]
    return out


def _autofill_targets() -> list[tuple[Path, str]]:
    """返回 (sqlite 文件, 删除语句) 列表。"""
    out: list[tuple[Path, str]] = []
    for root in (_chrome_root(), _edge_root()):
        for prof in _chromium_profile_dirs(root):
            wd = prof / "Web Data"
            if wd.exists():
                out.append((wd, "DELETE FROM autofill"))
    for prof in _firefox_profile_dirs():
        fh = prof / "formhistory.sqlite"
        if fh.exists():
            out.append((fh, "DELETE FROM moz_formhistory"))
    return out


# --------------------------------------------------------------------------------------
# 网络
# --------------------------------------------------------------------------------------
def _inet_cache_dirs() -> list[Path]:
    out = []
    for base in ("LOCALAPPDATA", "APPDATA"):
        v = os.environ.get(base)
        if v:
            out.append(Path(v) / "Microsoft" / "Windows" / "INetCache")
    return out


def _downloads_residue_patterns() -> list[str]:
    home = os.environ.get("USERPROFILE")
    if not home:
        return []
    d = Path(home) / "Downloads"
    out = []
    for ext in ("*.tmp", "*.crdownload", "*.part", "*.partial", "*.download"):
        out.append(str(d / ext))
    return out


def _reg_read_values(root, subkey: str) -> dict:
    out: dict = {}
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as h:
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


def _reg_subkeys(root, subkey: str) -> list[str]:
    out = []
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as h:
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


def _reg_backup(root, subkey: str, tag: str, log: LogFn) -> str:
    """导出注册表键做备份，返回备份文件路径（失败返回空串）。"""
    HIVE = {winreg.HKEY_CURRENT_USER: "HKCU", winreg.HKEY_LOCAL_MACHINE: "HKLM"}
    hive = HIVE.get(root)
    if not hive:
        return ""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{tag}_{ts}.reg"
    try:
        proc = _run(["reg", "export", f"{hive}\\{subkey}", str(dest), "/y"], timeout=60)
        if proc.returncode == 0 and dest.exists():
            log(f"已备份注册表: {dest.name}")
            return str(dest)
        log(f"注册表备份失败: {hive}\\{subkey}")
    except Exception as exc:
        log(f"注册表备份异常: {exc}")
    return ""


def _rdp_history_scan() -> tuple[int, int]:
    items = 0
    for root, sub in (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Terminal Server Client\Default"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Terminal Server Client\Servers"),
    ):
        if sub.endswith("Servers"):
            items += len(_reg_subkeys(root, sub))
        else:
            items += len(_reg_read_values(root, sub))
    return items, 0


def _rdp_history_clean(log: LogFn) -> dict:
    removed = 0
    base = r"Software\Microsoft\Terminal Server Client"
    _reg_backup(winreg.HKEY_CURRENT_USER, base, "rdp_history", log)
    for sub, is_key in (
        (base + r"\Default", False),
        (base + r"\Servers", True),
    ):
        try:
            if is_key:
                for name in _reg_subkeys(winreg.HKEY_CURRENT_USER, sub):
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub + "\\" + name)
                    removed += 1
            else:
                names = list(_reg_read_values(winreg.HKEY_CURRENT_USER, sub).keys())
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub, 0, winreg.KEY_SET_VALUE) as h:
                    for name in names:
                        try:
                            winreg.DeleteValue(h, name)
                            removed += 1
                        except OSError:
                            pass
        except OSError as exc:
            log(f"远程桌面历史清理跳过: {exc}")
    log(f"已清除远程桌面连接历史 {removed} 项")
    return {"removed": removed, "freed": 0, "skipped": 0, "note": ""}


def _mapped_drive_scan() -> tuple[int, int]:
    items = len(_reg_subkeys(winreg.HKEY_CURRENT_USER, "Network"))
    items += len(_reg_subkeys(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Map Network Drive MRU"))
    return items, 0


def _mapped_drive_clean(log: LogFn) -> dict:
    removed = 0
    for sub in (
        "Network",
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Map Network Drive MRU",
    ):
        _reg_backup(winreg.HKEY_CURRENT_USER, sub, "net_drive", log)
        for name in _reg_subkeys(winreg.HKEY_CURRENT_USER, sub):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub + "\\" + name)
                removed += 1
            except OSError:
                pass
    log(f"已清除网络驱动器/共享记录 {removed} 项")
    return {"removed": removed, "freed": 0, "skipped": 0, "note": ""}


_PROXY_VALUES = ["ProxyEnable", "ProxyServer", "ProxyOverride", "AutoConfigURL"]


def _proxy_scan() -> tuple[int, int]:
    vals = _reg_read_values(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
    )
    return sum(1 for v in _PROXY_VALUES if v in vals), 0


def _proxy_clean(log: LogFn) -> dict:
    sub = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    _reg_backup(winreg.HKEY_CURRENT_USER, sub, "proxy", log)
    removed = 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub, 0, winreg.KEY_SET_VALUE) as h:
            for name in _PROXY_VALUES:
                try:
                    winreg.DeleteValue(h, name)
                    removed += 1
                except OSError:
                    pass
    except OSError as exc:
        log(f"代理设置清理跳过: {exc}")
    log(f"已清除代理配置 {removed} 项（如需上网请重新设置代理）")
    return {"removed": removed, "freed": 0, "skipped": 0, "note": "需要时请重新配置代理"}


def _cmdkey_list() -> list[str]:
    try:
        proc = _run(["cmdkey", "/list"], timeout=30)
    except Exception:
        return []
    targets = re.findall(r"(?:Target|目标)\s*[:：]\s*(.+)", proc.stdout or "")
    return [t.strip() for t in targets if t.strip()]


def _network_credentials_scan() -> tuple[int, int]:
    return len(_cmdkey_list()), 0


def _network_credentials_clean(log: LogFn) -> dict:
    targets = _cmdkey_list()
    removed = 0
    for t in targets:
        try:
            proc = _run(["cmdkey", f"/delete:{t}"], timeout=30)
            if proc.returncode == 0:
                removed += 1
        except Exception:
            pass
    log(f"已删除保存的网络凭据 {removed} 条（下次连接需重新输入密码）")
    return {"removed": removed, "freed": 0, "skipped": len(targets) - removed, "note": ""}


def _clean_dns_cache(log: LogFn) -> dict:
    try:
        proc = _run(["ipconfig", "/flushdns"], timeout=60)
        ok = proc.returncode == 0
        log("DNS 缓存已刷新" if ok else f"DNS 刷新返回码 {proc.returncode}")
        return {"removed": 1 if ok else 0, "freed": 0, "skipped": 0 if ok else 1, "note": ""}
    except Exception as exc:
        log(f"DNS 刷新异常: {exc}")
        return {"removed": 0, "freed": 0, "skipped": 1, "note": str(exc)}


def _scan_downloads_residue() -> tuple[int, int]:
    return _stats_all(_downloads_residue_patterns())


def _clean_downloads_residue(log: LogFn) -> dict:
    log("清理下载目录中的未完成文件")
    return _clean_glob(_downloads_residue_patterns(), log).result()


def _scan_browser_autofill() -> tuple[int, int]:
    files = 0
    for path, _sql in _autofill_targets():
        if path.exists():
            files += 1
    return files, 0


def _clean_browser_autofill(log: LogFn) -> dict:
    """只删除表单历史行，不动密码、书签、Cookie。"""
    removed = 0
    skipped = 0
    for path, sql in _autofill_targets():
        try:
            conn = sqlite3.connect(str(path), timeout=3)
            try:
                cur = conn.cursor()
                cur.execute(sql)
                removed += max(cur.rowcount, 0)
                conn.commit()
                log(f"已清理自动填充记录: {path.name}")
            finally:
                conn.close()
        except Exception as exc:
            skipped += 1
            log(f"跳过 {path.name}（浏览器可能正在运行）: {type(exc).__name__}")
    return {"removed": removed, "freed": 0, "skipped": skipped, "note": "仅清除表单历史"}


# --------------------------------------------------------------------------------------
# 系统维护
# --------------------------------------------------------------------------------------
def _update_cache_dir() -> Path:
    return windows_dir() / "SoftwareDistribution" / "Download"


def _scan_update_cache() -> tuple[int, int]:
    return dir_stats(_update_cache_dir())


def _clean_update_cache(log: LogFn) -> dict:
    target = _update_cache_dir()
    if not target.is_dir():
        log("Windows 更新缓存目录不存在，跳过")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": ""}
    was_running = False
    try:
        q = _run(["sc", "query", "wuauserv"], timeout=15)
        if q.returncode == 0 and "RUNNING" in (q.stdout or "").upper():
            was_running = True
            _run(["sc", "stop", "wuauserv"], timeout=30)
            import time
            for _ in range(10):
                time.sleep(1)
                q2 = _run(["sc", "query", "wuauserv"], timeout=10)
                if "STOPPED" in (q2.stdout or "").upper():
                    break
    except Exception as exc:
        log(f"服务状态检测失败: {exc}")
    c = _clean_dir(target, log)
    if was_running:
        try:
            _run(["sc", "start", "wuauserv"], timeout=30)
            log("wuauserv 服务已恢复")
        except Exception:
            log("wuauserv 服务启动失败，可手动执行 sc start wuauserv")
    return c.result()


_STARTUP_KEYS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
]


def _exe_exists(command: str) -> bool:
    if not command:
        return True
    cmd = command.strip()
    m = re.match(r'^"([^"]+)"', cmd)
    if m:
        path = m.group(1)
    else:
        path = cmd.split(" ")[0]
    path = os.path.expandvars(path)
    if not os.path.isabs(path):
        return True  # 非绝对路径不做判断，避免误删
    return os.path.exists(path)


def _invalid_startup_entries() -> list[tuple[object, str, str]]:
    out = []
    for root, sub in _STARTUP_KEYS:
        for name, value in _reg_read_values(root, sub).items():
            if isinstance(value, str) and not _exe_exists(value):
                out.append((root, sub, name))
    return out


def _scan_invalid_startup() -> tuple[int, int]:
    return len(_invalid_startup_entries()), 0


def _clean_invalid_startup(log: LogFn) -> dict:
    entries = _invalid_startup_entries()
    if not entries:
        log("未发现无效启动项")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": ""}
    backed: set = set()
    removed = 0
    for root, sub, name in entries:
        key = (root, sub)
        if key not in backed:
            _reg_backup(root, sub, "startup", log)
            backed.add(key)
        try:
            with winreg.OpenKey(root, sub, 0, winreg.KEY_SET_VALUE) as h:
                winreg.DeleteValue(h, name)
                removed += 1
                log(f"已移除无效启动项: {name}")
        except OSError as exc:
            log(f"移除失败 {name}: {exc}")
    return {"removed": removed, "freed": 0, "skipped": len(entries) - removed, "note": ""}


_UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]


def _uninstall_residue_entries() -> list[tuple[object, str, str, str]]:
    out = []
    for root, sub in _UNINSTALL_KEYS:
        for name in _reg_subkeys(root, sub):
            full = sub + "\\" + name
            vals = _reg_read_values(root, full)
            if not vals.get("DisplayName"):
                continue
            if vals.get("SystemComponent") in (1, "1"):
                continue
            loc = vals.get("InstallLocation") or ""
            if not loc or not os.path.isabs(os.path.expandvars(str(loc))):
                continue
            if not os.path.exists(os.path.expandvars(str(loc))):
                out.append((root, sub, name, str(vals.get("DisplayName"))))
    return out


def _scan_uninstall_residue() -> tuple[int, int]:
    return len(_uninstall_residue_entries()), 0


def _clean_uninstall_residue(log: LogFn) -> dict:
    entries = _uninstall_residue_entries()
    if not entries:
        log("未发现卸载残留项")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": ""}
    backed: set = set()
    removed = 0
    for root, sub, name, display in entries:
        key = (root, sub)
        if key not in backed:
            _reg_backup(root, sub, "uninstall_residue", log)
            backed.add(key)
        try:
            winreg.DeleteKey(root, sub + "\\" + name)
            removed += 1
            log(f"已移除卸载残留: {display}")
        except OSError as exc:
            log(f"移除失败 {display}: {exc}")
    return {"removed": removed, "freed": 0, "skipped": len(entries) - removed, "note": ""}


def _scan_winsxs() -> tuple[int, int]:
    return 0, 0


def _clean_winsxs(log: LogFn) -> dict:
    log("正在执行 DISM 组件清理（可能需要几分钟）...")
    try:
        proc = _run(["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"], timeout=1800)
    except Exception as exc:
        log(f"DISM 执行异常: {exc}")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": str(exc)}
    if proc.returncode == 0:
        log("DISM 组件清理完成")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": "已完成"}
    log(f"DISM 返回码 {proc.returncode}")
    for line in (proc.stdout or "").splitlines()[-6:]:
        if line.strip():
            log("  " + line.strip())
    return {"removed": 0, "freed": 0, "skipped": 0, "note": f"返回码 {proc.returncode}"}


def _windows_old_dir() -> Path:
    return windows_dir().parent / "Windows.old"


def _scan_windows_old() -> tuple[int, int]:
    d = _windows_old_dir()
    if not d.is_dir():
        return 0, 0
    return dir_stats(d)


def _clean_windows_old(log: LogFn) -> dict:
    d = _windows_old_dir()
    if not d.is_dir():
        log("未发现 Windows.old 目录")
        return {"removed": 0, "freed": 0, "skipped": 0, "note": ""}
    _files, size = dir_stats(d)
    log("正在删除旧的 Windows 安装文件（耗时较长）...")
    try:
        _run(["takeown", "/F", str(d), "/R", "/A", "/D", "Y"], timeout=1800)
        _run(["icacls", str(d), "/grant", "*S-1-5-32-544:F", "/T", "/C", "/Q"], timeout=1800)
        proc = _run(["cmd", "/c", "rd", "/s", "/q", str(d)], timeout=3600)
        if not d.exists():
            log(f"Windows.old 已删除，释放约 {size / 1073741824:.2f} GB")
            return {"removed": 1, "freed": size, "skipped": 0, "note": ""}
        log(f"删除未完成，返回码 {proc.returncode}")
        return {"removed": 0, "freed": 0, "skipped": 1, "note": "部分文件仍被占用"}
    except Exception as exc:
        return {"removed": 0, "freed": 0, "skipped": 1, "note": str(exc)}


# --------------------------------------------------------------------------------------
# 注册表
# --------------------------------------------------------------------------------------
ITEMS: list[CleanItem] = [
    CleanItem(
        "temp_user", "用户临时文件", "清理当前用户 TEMP/TMP 目录中的全部临时文件",
        "系统缓存", RISK_SAFE, False, True, _scan_temp_user, _clean_temp_user,
    ),
    CleanItem(
        "temp_system", "系统临时文件", "清理 C:\\Windows\\Temp",
        "系统缓存", RISK_SAFE, True, True, _scan_temp_system, _clean_temp_system,
    ),
    CleanItem(
        "crash_dumps", "崩溃转储与错误报告", "清理 CrashDumps 与 Windows 错误报告队列",
        "系统缓存", RISK_SAFE, False, True, _scan_crash_dumps, _clean_crash_dumps,
    ),
    CleanItem(
        "thumb_cache", "缩略图与图标缓存", "清理资源管理器的缩略图/图标缓存数据库",
        "系统缓存", RISK_SAFE, False, True, _scan_thumb_cache, _clean_thumb_cache,
    ),
    CleanItem(
        "recycle_bin", "清空回收站", "清空所有驱动器的回收站内容",
        "系统缓存", RISK_NORMAL, False, True, _recycle_bin_scan, _clean_recycle_bin,
    ),
    CleanItem(
        "chrome_cache", "Chrome 浏览器缓存", "清理 Chrome 各用户配置的 Cache/Code Cache/GPUCache 等",
        "浏览器", RISK_SAFE, False, True,
        lambda: _scan_dirs([Path(p) for p in _chromium_cache_paths(_chrome_root())]),
        lambda log: _clean_dirs([Path(p) for p in _chromium_cache_paths(_chrome_root())], log),
    ),
    CleanItem(
        "edge_cache", "Edge 浏览器缓存", "清理 Edge 各用户配置的 Cache/Code Cache/GPUCache 等",
        "浏览器", RISK_SAFE, False, True,
        lambda: _scan_dirs([Path(p) for p in _chromium_cache_paths(_edge_root())]),
        lambda log: _clean_dirs([Path(p) for p in _chromium_cache_paths(_edge_root())], log),
    ),
    CleanItem(
        "firefox_cache", "Firefox 浏览器缓存", "清理 Firefox 各配置的 cache2/startupCache/shader-cache",
        "浏览器", RISK_SAFE, False, True,
        lambda: _scan_dirs(_firefox_cache_paths()),
        lambda log: _clean_dirs(_firefox_cache_paths(), log),
    ),
    CleanItem(
        "browser_autofill", "浏览器表单自动填充记录", "删除表单填写历史（不含已保存的密码）",
        "浏览器", RISK_NORMAL, False, False, _scan_browser_autofill, _clean_browser_autofill,
    ),
    CleanItem(
        "network_temp", "网络临时文件", "清理 INetCache 与 Temporary Internet Files",
        "网络", RISK_SAFE, False, True,
        lambda: _scan_dirs(_inet_cache_dirs()),
        lambda log: _clean_dirs(_inet_cache_dirs(), log),
    ),
    CleanItem(
        "dns_cache", "DNS 缓存", "执行 ipconfig /flushdns 刷新域名解析缓存",
        "网络", RISK_SAFE, True, True, lambda: (0, 0), _clean_dns_cache,
    ),
    CleanItem(
        "downloads_residue", "下载目录残留", "删除下载目录中的 *.tmp / *.crdownload / *.part 等未完成文件",
        "网络", RISK_NORMAL, False, False, _scan_downloads_residue, _clean_downloads_residue,
    ),
    CleanItem(
        "rdp_history", "远程桌面连接历史", "清除 mstsc 连接地址记录（MRU）",
        "网络", RISK_NORMAL, False, False, _rdp_history_scan, _rdp_history_clean,
    ),
    CleanItem(
        "mapped_drive_history", "网络驱动器与共享记录", "清除映射驱动器与网络共享访问历史",
        "网络", RISK_NORMAL, False, False, _mapped_drive_scan, _mapped_drive_clean,
    ),
    CleanItem(
        "proxy_settings", "代理设置残留", "清除系统代理配置（清除后需重新配置才能上网）",
        "网络", RISK_HIGH, False, False, _proxy_scan, _proxy_clean,
    ),
    CleanItem(
        "network_credentials", "保存的网络凭据", "删除凭据管理器中保存的网络/共享密码",
        "网络", RISK_HIGH, False, False, _network_credentials_scan, _network_credentials_clean,
    ),
    CleanItem(
        "update_cache", "Windows 更新缓存", "清理 SoftwareDistribution\\Download 下载缓存",
        "系统维护", RISK_NORMAL, True, False, _scan_update_cache, _clean_update_cache,
    ),
    CleanItem(
        "invalid_startup", "无效启动项", "移除指向已不存在程序的启动项（删除前自动备份注册表）",
        "系统维护", RISK_NORMAL, True, False, _scan_invalid_startup, _clean_invalid_startup,
    ),
    CleanItem(
        "uninstall_residue", "卸载残留项", "移除 InstallLocation 已不存在的卸载记录（删除前自动备份）",
        "系统维护", RISK_NORMAL, True, False, _scan_uninstall_residue, _clean_uninstall_residue,
    ),
    CleanItem(
        "winsxs", "WinSxS 组件清理", "执行 DISM 清理组件存储，耗时较长",
        "系统维护", RISK_HIGH, True, False, _scan_winsxs, _clean_winsxs,
    ),
    CleanItem(
        "windows_old", "旧版 Windows 安装文件", "删除 C:\\Windows.old，释放大量空间且不可恢复",
        "系统维护", RISK_HIGH, True, False, _scan_windows_old, _clean_windows_old,
    ),
]


def _item_by_key(key: str) -> CleanItem | None:
    for it in ITEMS:
        if it.key == key:
            return it
    return None


RISK_LABEL = {RISK_SAFE: "安全", RISK_NORMAL: "常规", RISK_HIGH: "高危"}
