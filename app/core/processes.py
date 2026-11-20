"""进程检测：清理前判断目标程序是否正在运行。"""
from __future__ import annotations

import os
import subprocess


def running_processes(names: tuple[str, ...] | list[str]) -> list[str]:
    """返回 names 中正在运行的进程名（不区分大小写）。"""
    wanted = [n for n in (names or ()) if n]
    if not wanted:
        return []
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="ignore", timeout=8,
            creationflags=flags,
        )
        output = (proc.stdout or "").lower()
    except Exception:
        return []
    return [name for name in wanted if name.lower() in output]

def running_image_names() -> set[str]:
    """返回当前进程映像名（小写，含 .exe）。"""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="ignore", timeout=8,
            creationflags=flags,
        )
    except Exception:
        return set()
    names: set[str] = set()
    for line in (proc.stdout or "").splitlines():
        if not line.strip():
            continue
        first = line.split(",", 1)[0].strip().strip('"').lower()
        if first:
            names.add(first)
    return names

