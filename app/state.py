"""全局应用状态。"""
from __future__ import annotations

from .core.engine import ScanOutcome
from .core.hardware import build_sections, collect
from .core.items import ITEMS, CleanItem
from .data.db import get_db
from .data.hwid import machine_code, machine_name, user_name
from .demo_data import demo_clean_items


class AppState:
    def __init__(self) -> None:
        self.db = get_db()
        self.hwid = machine_code()
        self.machine = machine_name()
        self.user = user_name()
        self.items: list[CleanItem] = list(ITEMS) + demo_clean_items()
        self.selected: dict[str, bool] = {it.key: it.default_selected for it in self.items}
        self.last_scan: dict[str, ScanOutcome] = {}

        self.theme_mode: str = self.db.get_setting("theme", "light")
        self.auto_backup: bool = self.db.get_setting("auto_backup", "1") == "1"
        self.history_keep: int = int(self.db.get_setting("history_keep", "500") or 500)

        # 硬件信息（后台线程采集后写入）
        self.hardware: dict | None = None
        self.hw_sections: list = []
        self.hw_loading: bool = False
        self.hw_error: str = ""

    # ---------------------------------------------------------------- 清理项
    def item(self, key: str) -> CleanItem | None:
        for it in self.items:
            if it.key == key:
                return it
        return None

    def scanned_size(self, key: str) -> int:
        outcome = self.last_scan.get(key)
        return outcome.size if outcome else 0

    def total_scanned_size(self) -> int:
        return sum(o.size for o in self.last_scan.values())

    def save_setting(self, key: str, value) -> None:
        self.db.set_setting(key, value)

    # ---------------------------------------------------------------- 硬件信息
    def load_hardware(self) -> dict:
        """同步采集硬件信息（建议在后台线程调用）。"""
        self.hw_loading = True
        try:
            data = collect()
            self.hardware = data
            self.hw_sections = build_sections(data)
            self.hw_error = "" if data.get("ok") else "部分信息通过注册表回退读取"
        except Exception as exc:  # pragma: no cover
            self.hw_error = f"读取失败: {exc}"
        finally:
            self.hw_loading = False
        return self.hardware or {}

    def hardware_ready(self) -> bool:
        return bool(self.hw_sections)


state = AppState()
