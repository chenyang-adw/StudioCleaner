"""其他工具的后端实现。"""
from __future__ import annotations

import os
from pathlib import Path


def find_big_files(root: str, min_mb: int = 100, limit: int = 300,
                   progress=None) -> list[tuple[str, int]]:
    """扫描目录下超过 min_mb 的文件，按大小倒序返回。"""
    root_path = Path(root)
    if not root_path.is_dir():
        raise ValueError("目录不存在")
    threshold = max(1, int(min_mb)) * 1024 * 1024
    found: list[tuple[str, int]] = []
    scanned = 0
    for current, dirs, files in os.walk(root_path, onerror=lambda e: None, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
        for name in files:
            path = os.path.join(current, name)
            if os.path.islink(path):
                continue
            scanned += 1
            if progress and scanned % 500 == 0:
                progress(scanned, 0)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size >= threshold:
                found.append((path, size))
    found.sort(key=lambda item: item[1], reverse=True)
    return found[:limit]


def find_empty_dirs(root: str, limit: int = 3000, progress=None) -> list[str]:
    """自底向上找出空目录（不含根目录本身）。"""
    root_path = Path(root)
    if not root_path.is_dir():
        raise ValueError("目录不存在")
    empty: list[str] = []
    for current, dirs, files in os.walk(root_path, topdown=False,
                                        onerror=lambda e: None, followlinks=False):
        if Path(current) == root_path:
            continue
        try:
            if os.path.islink(current):
                continue
            entries = os.listdir(current)
        except OSError:
            continue
        if not entries:
            empty.append(current)
            if len(empty) >= limit:
                break
        if progress:
            progress(len(empty), 0)
    return empty


def delete_empty_dirs(paths: list[str]) -> tuple[int, list[str]]:
    ok = 0
    fails: list[str] = []
    for path in sorted(paths, key=len, reverse=True):
        try:
            os.rmdir(path)
            ok += 1
        except OSError as exc:
            fails.append(f"{path}：{exc}")
    return ok, fails


def size_text(n: int) -> str:
    value = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return "-"
