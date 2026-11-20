"""清理页：扫描、勾选、执行。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    ProgressBar,
    SegmentedWidget,
    TextEdit,
)

from ...core.items import RISK_HIGH
from ...core.sizes import human_size
from ...state import state
from ..theme import palette
from ..widgets.base import Page, SectionCard, StatCard
from ..widgets.buttons import GradientButton, OutlineButton
from ..widgets.itemcard import CleanItemCard
from ..worker import CleanWorker, ScanWorker


class CleanPage(Page):
    finished_clean = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("清理", "勾选需要的项目，先扫描再清理", parent)
        self._cards: dict[str, CleanItemCard] = {}
        self._scan_worker: ScanWorker | None = None
        self._clean_worker: CleanWorker | None = None
        self._category = "全部分类"
        self.categories = list(dict.fromkeys(it.category for it in state.items))

        self.add_widget(self._build_toolbar())
        self.add_widget(self._build_insight())
        self._build_items()
        self.add_widget(self._build_progress())
        self.add_widget(self._build_log())
        self.add_stretch()
        self._update_summary()

    # ------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> QWidget:
        card = SectionCard("清理项", "只包含缓存、临时文件、日志、网络残留与系统维护类项目", FIF.BROOM)

        self.seg = SegmentedWidget()
        self.seg.addItem("全部分类", "全部")
        for c in self.categories:
            self.seg.addItem(c, c)
        self.seg.setCurrentItem("全部分类")
        self.seg.currentItemChanged.connect(self._on_category)
        card.content_layout.addWidget(self.seg)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.search = LineEdit()
        self.search.setPlaceholderText("搜索清理项…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        self.search.setMinimumWidth(200)
        bar.addWidget(self.search, 1)

        self.btn_all = OutlineButton("全选")
        self.btn_all.clicked.connect(lambda: self._bulk_select("all"))
        bar.addWidget(self.btn_all)
        self.btn_safe = OutlineButton("仅安全项")
        self.btn_safe.clicked.connect(lambda: self._bulk_select("safe"))
        bar.addWidget(self.btn_safe)
        self.btn_none = OutlineButton("全不选")
        self.btn_none.clicked.connect(lambda: self._bulk_select("none"))
        bar.addWidget(self.btn_none)

        bar.addSpacing(6)
        self.btn_scan = OutlineButton("扫描")
        self.btn_scan.clicked.connect(self.start_scan)
        bar.addWidget(self.btn_scan)
        self.btn_run = GradientButton("执行清理")
        self.btn_run.clicked.connect(self.start_clean)
        bar.addWidget(self.btn_run)
        card.content_layout.addLayout(bar)

        self.summary_label = BodyLabel("已选择 0 项　·　预计可释放 -")
        self.summary_label.setStyleSheet(f"color:{palette()['sub']};")
        card.content_layout.addWidget(self.summary_label)
        return card

    def _build_insight(self) -> QWidget:
        card = SectionCard("清理建议", "按 2026 年常见占用排序（演示数据）", FIF.PIE_SINGLE)
        row = QHBoxLayout()
        row.setSpacing(12)
        items = (
            (FIF.DEVELOPER_TOOLS, "开发者缓存", "3.2 GB", "npm / pip / Cargo / Go", "#4C6FFF"),
            (FIF.ROBOT, "AI 工具缓存", "1.1 GB", "ChatGPT / 豆包 / DeepSeek", "#8B5CF6"),
            (FIF.ZIP_FOLDER, "项目构建产物", "4.8 GB", "3 个项目 · 12 个产物", "#F59E0B"),
        )
        for icon, title, value, hint, color in items:
            row.addWidget(StatCard(icon, title, value, hint, color, card))
        card.content_layout.addLayout(row)
        return card

    def _on_category(self, key: str) -> None:
        self._category = key
        self._apply_filter()

    # ------------------------------------------------------------- items
    def _build_items(self) -> None:
        self.items_holder = QWidget()
        self.items_layout = QVBoxLayout(self.items_holder)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        self._render_items()
        self.add_widget(self.items_holder)

    def _render_items(self) -> None:
        while self.items_layout.count():
            it = self.items_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
        self._cards.clear()
        self._cat_headers: dict[str, QLabel] = {}
        for cat in self.categories:
            header = CaptionLabel(cat)
            header.setStyleSheet(f"color:{palette()['sub']};font-weight:600;padding-top:6px;")
            self.items_layout.addWidget(header)
            self._cat_headers[cat] = header
            for item in state.items:
                if item.category != cat:
                    continue
                card = CleanItemCard(item)
                card.toggled.connect(self._on_toggle)
                self.items_layout.addWidget(card)
                self._cards[item.key] = card
        self._apply_filter()

    def _apply_filter(self) -> None:
        cat = self._category or "全部分类"
        text = self.search.text().strip().lower()
        for cat_name, header in self._cat_headers.items():
            header_visible = False
            for item in state.items:
                if item.category != cat_name:
                    continue
                card = self._cards.get(item.key)
                if card is None:
                    continue
                ok_cat = cat in ("全部分类", cat_name)
                ok_text = (not text) or text in item.label.lower() or text in item.desc.lower()
                visible = ok_cat and ok_text
                card.setVisible(visible)
                header_visible = header_visible or visible
            header.setVisible(header_visible)

    def _on_toggle(self, key: str, checked: bool) -> None:
        state.selected[key] = checked
        self._update_summary()

    def _bulk_select(self, mode: str) -> None:
        for item in state.items:
            card = self._cards.get(item.key)
            if card is None or not card.isVisible():
                continue
            if mode == "all":
                value = True
            elif mode == "none":
                value = False
            else:
                value = item.risk != RISK_HIGH
            card.set_checked(value)
            state.selected[item.key] = value
        self._update_summary()

    def _update_summary(self) -> None:
        chosen = [it for it in state.items if state.selected.get(it.key)]
        total = sum(state.scanned_size(it.key) for it in chosen)
        self.summary_label.setText(
            f"已选择 {len(chosen)} 项　·　预计可释放 {human_size(total) if state.last_scan else '-'}"
        )

    # ------------------------------------------------------------- progress / log
    def _build_progress(self) -> QWidget:
        card = SectionCard("执行进度", "", FIF.SPEED_HIGH)
        self.progress = ProgressBar()
        self.progress.setValue(0)
        card.content_layout.addWidget(self.progress)
        self.status_label = CaptionLabel("就绪")
        self.status_label.setStyleSheet(f"color:{palette()['sub']};")
        card.content_layout.addWidget(self.status_label)
        return card

    def _build_log(self) -> QWidget:
        card = SectionCard("运行日志", "", FIF.DOCUMENT)
        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(150)
        self.log_box.setPlaceholderText("清理过程中的详细信息会显示在这里")
        card.content_layout.addWidget(self.log_box)
        clear_row = QHBoxLayout()
        clear_row.addStretch(1)
        btn_clear = OutlineButton("清空日志")
        btn_clear.clicked.connect(self.log_box.clear)
        clear_row.addWidget(btn_clear)
        card.content_layout.addLayout(clear_row)
        return card

    def _log(self, text: str) -> None:
        self.log_box.append(text)

    # ------------------------------------------------------------- actions
    def start_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.log_box.clear()
        self.progress.setValue(0)
        self.status_label.setText("正在扫描…")
        self.btn_scan.setEnabled(False)
        self.btn_run.setEnabled(False)
        self._scan_worker = ScanWorker(state.items, self)
        self._scan_worker.progress.connect(self._on_progress)
        self._scan_worker.log.connect(self._log)
        self._scan_worker.done.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_done(self, outcomes) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_run.setEnabled(True)
        state.last_scan = {o.key: o for o in outcomes}
        for key, outcome in state.last_scan.items():
            card = self._cards.get(key)
            if card is None:
                continue
            if outcome.error:
                card.set_size_text(outcome.error, is_error=True)
            else:
                card.set_size_text(human_size(outcome.size))
        total = sum(o.size for o in outcomes)
        self.status_label.setText(f"扫描完成：{len(outcomes)} 项，共可释放约 {human_size(total)}")
        self._update_summary()
        self.finished_clean.emit()

    def start_clean(self) -> None:
        if self._clean_worker and self._clean_worker.isRunning():
            return
        chosen = [it for it in state.items if state.selected.get(it.key)]
        if not chosen:
            InfoBar.warning("未选择清理项", "请至少勾选一个项目", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2500)
            return
        high = [it for it in chosen if it.risk == RISK_HIGH]
        if high:
            names = "\n".join(f"· {it.label}" for it in high)
            box = MessageBox(
                "高危项目确认",
                f"以下项目属于高危操作，可能影响系统设置或不可恢复：\n\n{names}\n\n确定继续吗？",
                self,
            )
            box.yesButton.setText("继续清理")
            box.cancelButton.setText("取消")
            if not box.exec():
                return
        self.log_box.clear()
        self.progress.setValue(0)
        self.status_label.setText("正在清理…")
        self.btn_scan.setEnabled(False)
        self.btn_run.setEnabled(False)
        self._clean_worker = CleanWorker(chosen, self)
        self._clean_worker.progress.connect(self._on_progress)
        self._clean_worker.log.connect(self._log)
        self._clean_worker.done.connect(self._on_clean_done)
        self._clean_worker.start()

    def _on_progress(self, current: int, total: int, text: str) -> None:
        value = int(current / total * 100) if total else 0
        self.progress.setValue(value)
        self.status_label.setText(text)

    def _on_clean_done(self, outcomes) -> None:
        self.btn_scan.setEnabled(True)
        self.btn_run.setEnabled(True)
        self.progress.setValue(100)
        total_removed = sum(o.removed for o in outcomes)
        total_freed = sum(o.freed for o in outcomes)
        success = sum(1 for o in outcomes if o.ok and not o.error)

        for o in outcomes:
            state.db.add_history(
                o.key, o.label, o.category, bool(o.ok and not o.error),
                o.removed, o.freed, o.skipped, o.error or o.note,
            )
        state.db.add_session(len(outcomes), success, total_removed, total_freed, state.user)
        state.db.trim_history(state.history_keep)

        self.status_label.setText(
            f"清理完成：成功 {success}/{len(outcomes)} 项，清理 {total_removed} 项，"
            f"释放 {human_size(total_freed)}"
        )
        InfoBar.success(
            "清理完成",
            f"成功 {success}/{len(outcomes)} 项，释放 {human_size(total_freed)}",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000,
        )
        for key in state.last_scan:
            card = self._cards.get(key)
            if card is not None:
                card.set_size_text("已清理")
        state.last_scan = {}
        self._update_summary()
        self.finished_clean.emit()
