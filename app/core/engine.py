"""扫描 / 清理执行引擎（与界面解耦，可单独调用）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .admin import is_admin
from .items import CleanItem
from .processes import running_processes


@dataclass
class ScanOutcome:
    key: str
    label: str
    category: str
    count: int = 0
    size: int = 0
    error: str = ""


@dataclass
class CleanOutcome:
    key: str
    label: str
    category: str
    ok: bool = False
    removed: int = 0
    freed: int = 0
    skipped: int = 0
    note: str = ""
    error: str = ""


ProgressFn = Callable[[int, int, str], None]
LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


def scan_items(
    items: Iterable[CleanItem],
    on_progress: ProgressFn | None = None,
    on_log: LogFn | None = None,
    should_cancel: CancelFn | None = None,
) -> list[ScanOutcome]:
    items = list(items)
    total = len(items)
    outcomes: list[ScanOutcome] = []
    admin = is_admin()
    for idx, item in enumerate(items, start=1):
        if should_cancel and should_cancel():
            break
        if on_progress:
            on_progress(idx - 1, total, f"正在统计：{item.label}")
        outcome = ScanOutcome(item.key, item.label, item.category)
        if item.requires_admin and not admin:
            outcome.error = "需要管理员权限"
        else:
            try:
                count, size = item.scan()
                outcome.count = int(count or 0)
                outcome.size = int(size or 0)
            except Exception as exc:  # pragma: no cover
                outcome.error = f"{type(exc).__name__}: {exc}"
        outcomes.append(outcome)
        if on_log:
            if outcome.error:
                on_log(f"[跳过] {item.label} —— {outcome.error}")
            else:
                on_log(f"[统计] {item.label}：{outcome.count} 项")
    if on_progress:
        on_progress(total, total, "统计完成")
    return outcomes


def clean_items(
    items: Iterable[CleanItem],
    on_progress: ProgressFn | None = None,
    on_log: LogFn | None = None,
    should_cancel: CancelFn | None = None,
) -> list[CleanOutcome]:
    items = list(items)
    total = len(items)
    outcomes: list[CleanOutcome] = []
    admin = is_admin()
    for idx, item in enumerate(items, start=1):
        if should_cancel and should_cancel():
            if on_log:
                on_log("已取消剩余清理项")
            break
        if on_progress:
            on_progress(idx - 1, total, f"正在清理：{item.label}")
        outcome = CleanOutcome(item.key, item.label, item.category)
        blocked = running_processes(getattr(item, "blocked_by", ()))
        if item.requires_admin and not admin:
            outcome.error = "需要管理员权限"
            outcome.note = "请以管理员身份重新运行"
        elif blocked:
            outcome.error = "请先关闭：" + "、".join(blocked)
            outcome.note = "进程占用"
        else:
            try:
                result = item.clean(lambda m: on_log(f"    {m}") if on_log else None) or {}
                outcome.removed = int(result.get("removed", 0))
                outcome.freed = int(result.get("freed", 0))
                outcome.skipped = int(result.get("skipped", 0))
                outcome.note = result.get("note", "") or ""
                outcome.ok = outcome.removed > 0 or outcome.skipped == 0
            except Exception as exc:  # pragma: no cover
                outcome.error = f"{type(exc).__name__}: {exc}"
        outcomes.append(outcome)
        if on_log:
            if outcome.error:
                on_log(f"[失败] {item.label} —— {outcome.error}")
            else:
                on_log(
                    f"[完成] {item.label}：清理 {outcome.removed} 项"
                    + (f"，跳过 {outcome.skipped} 项" if outcome.skipped else "")
                )
    if on_progress:
        on_progress(total, total, "清理完成")
    return outcomes
