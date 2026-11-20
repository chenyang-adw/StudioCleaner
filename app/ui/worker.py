"""后台任务线程。"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..core.engine import clean_items, scan_items


class ScanWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    done = Signal(object)

    def __init__(self, items, parent=None) -> None:
        super().__init__(parent)
        self._items = list(items)
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            result = scan_items(
                self._items,
                on_progress=lambda a, b, c: self.progress.emit(a, b, c),
                on_log=lambda m: self.log.emit(m),
                should_cancel=lambda: self._cancel,
            )
        except Exception as exc:  # pragma: no cover
            self.log.emit(f"扫描异常: {exc}")
            result = []
        self.done.emit(result)


class CleanWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    done = Signal(object)

    def __init__(self, items, parent=None) -> None:
        super().__init__(parent)
        self._items = list(items)
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            result = clean_items(
                self._items,
                on_progress=lambda a, b, c: self.progress.emit(a, b, c),
                on_log=lambda m: self.log.emit(m),
                should_cancel=lambda: self._cancel,
            )
        except Exception as exc:  # pragma: no cover
            self.log.emit(f"清理异常: {exc}")
            result = []
        self.done.emit(result)


class HardwareWorker(QThread):
    """后台读取硬件信息（PowerShell CIM 首次调用约 3-5 秒）。"""

    done = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        from ..state import state
        data = state.load_hardware()
        self.done.emit(data)


class FuncWorker(QThread):
    """通用后台任务：把阻塞函数丢到子线程执行。"""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, parent=None, **kwargs) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))
            return
        self.done.emit(result)
