"""体积统计工具。"""
import os
from pathlib import Path


def human_size(n: float) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} TB"


def dir_stats(path) -> tuple[int, int]:
    """返回 (文件数, 字节数)。不跟随符号链接/联接点, 出错忽略。"""
    files = 0
    total = 0
    try:
        p = Path(path)
        if not p.exists():
            return 0, 0
        if p.is_file() and not p.is_symlink():
            try:
                return 1, p.stat().st_size
            except OSError:
                return 0, 0
        for root, dirs, names in os.walk(p, onerror=lambda e: None, followlinks=False):
            # 目录层面剔除符号链接, 避免越界
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for name in names:
                fp = os.path.join(root, name)
                if os.path.islink(fp):
                    continue
                try:
                    total += os.path.getsize(fp)
                    files += 1
                except OSError:
                    continue
    except Exception:
        pass
    return files, total


def disk_usage(path: str = "C:\\") -> tuple[int, int, int]:
    """返回 (总容量, 已用, 可用) 字节。"""
    try:
        usage = __import__("shutil").disk_usage(path)
        return usage.total, usage.used, usage.free
    except Exception:
        return 0, 0, 0
