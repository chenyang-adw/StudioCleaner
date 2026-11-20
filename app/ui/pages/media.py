"""照片视频总览：网格浏览、筛选、查看、清理（演示数据）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    SegmentedWidget,
    StrongBodyLabel,
)

from ...core.sizes import human_size
from ...demo_data import MEDIA_ITEMS, MediaItem
from ..theme import ACCENT, INFO, SUCCESS, WARNING, palette
from ..widgets.base import Page, SectionCard, StatCard
from ..widgets.buttons import GradientButton, OutlineButton, SoftButton
from ..widgets.media import MediaCard, MediaPreviewDialog


class MediaPage(Page):
    def __init__(self, parent=None) -> None:
        super().__init__("照片视频", "总览、查看与清理本机媒体（演示数据）", parent)
        self.items: list[MediaItem] = list(MEDIA_ITEMS)
        self._cleaned: set[str] = set()
        self._selected: set[str] = set()
        self._filter = "全部"
        self._cards: dict[str, MediaCard] = {}
        self._columns = 3

        self.add_widget(self._build_stats())
        self.add_widget(self._build_toolbar())
        self.add_widget(self._build_grid_card())
        self.add_widget(self._build_action_bar())
        self.add_stretch()
        self._rebuild_grid()
        self._update_stats()

    # ------------------------------------------------------------- stats
    def _build_stats(self) -> QWidget:
        host = QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.stat_photos = StatCard(FIF.PHOTO, "照片", "0", "演示数据", ACCENT, host)
        self.stat_videos = StatCard(FIF.VIDEO, "视频", "0", "演示数据", "#8B5CF6", host)
        self.stat_total = StatCard(FIF.SAVE, "媒体占用", "0 B", "照片 + 视频", INFO, host)
        self.stat_clean = StatCard(FIF.BROOM, "可清理", "0 B", "截图 / 重复 / 缓存", SUCCESS, host)
        for card in (self.stat_photos, self.stat_videos, self.stat_total, self.stat_clean):
            row.addWidget(card)
        return host

    # ------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> QWidget:
        card = SectionCard("媒体库", "勾选后可批量清理；点「查看」打开大图和详情", FIF.PHOTO)
        row = QHBoxLayout()
        row.setSpacing(8)

        self.seg = SegmentedWidget()
        for key in ("全部", "照片", "视频", "截图", "可清理", "重复"):
            self.seg.addItem(key, key)
        self.seg.setCurrentItem("全部")
        self.seg.currentItemChanged.connect(self._on_filter)
        row.addWidget(self.seg, 1)

        self.search = LineEdit()
        self.search.setPlaceholderText("搜索文件名或文件夹…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        self.search.setMinimumWidth(190)
        row.addWidget(self.search)

        self.sort = ComboBox()
        self.sort.addItem("按日期", userData="date")
        self.sort.addItem("按大小", userData="size")
        self.sort.addItem("按名称", userData="name")
        self.sort.currentIndexChanged.connect(lambda _i: self._rebuild_grid())
        row.addWidget(self.sort)
        card.content_layout.addLayout(row)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.count_label = CaptionLabel("")
        self.count_label.setStyleSheet(f"color:{palette()['sub']};")
        bar.addWidget(self.count_label)
        bar.addStretch(1)
        btn_pick = OutlineButton("全选可清理")
        btn_pick.clicked.connect(self._select_cleanable)
        bar.addWidget(btn_pick)
        btn_scan = GradientButton("扫描媒体")
        btn_scan.clicked.connect(self._scan)
        bar.addWidget(btn_scan)
        card.content_layout.addLayout(bar)
        return card

    # ------------------------------------------------------------- grid
    def _build_grid_card(self) -> QWidget:
        card = SectionCard("总览", "按日期倒序展示；可切换筛选与排序", FIF.TILES)
        self.grid_host = QWidget(card)
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        card.content_layout.addWidget(self.grid_host)
        return card

    def _rebuild_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.hide()
                w.deleteLater()
        self._cards.clear()

        for col in range(self._columns + 1):
            self.grid.setColumnStretch(col, 0)
        self.grid.setColumnStretch(self._columns, 1)
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        items = self._sorted_items()
        for index, item in enumerate(items):
            card = MediaCard(item, self.grid_host)
            card.view_requested.connect(self._open_preview)
            card.selection_changed.connect(self._on_selection)
            card.set_selected(item.name in self._selected)
            self.grid.addWidget(card, index // self._columns, index % self._columns)
            self._cards[item.name] = card

        self._apply_filter()
        self._update_bar()

    def _sorted_items(self) -> list[MediaItem]:
        mode = self.sort.currentData() if hasattr(self, "sort") else "date"
        items = list(self.items)
        if mode == "size":
            items.sort(key=lambda i: i.size, reverse=True)
        elif mode == "name":
            items.sort(key=lambda i: i.name.lower())
        else:
            items.sort(key=lambda i: i.date, reverse=True)
        return items

    def _match(self, item: MediaItem) -> bool:
        text = self.search.text().strip().lower() if hasattr(self, "search") else ""
        if text and text not in item.name.lower() and text not in item.folder.lower():
            return False
        if self._filter == "照片":
            return item.kind == "照片"
        if self._filter == "视频":
            return item.kind == "视频"
        if self._filter == "截图":
            return item.kind == "截图"
        if self._filter == "可清理":
            return item.cleanable and item.name not in self._cleaned
        if self._filter == "重复":
            return item.duplicate
        return True

    def _on_filter(self, key: str) -> None:
        self._filter = key
        self._apply_filter()
        self._update_bar()

    def _apply_filter(self) -> None:
        for name, card in self._cards.items():
            card.setVisible(self._match(card.item))
        visible = sum(1 for c in self._cards.values() if self._match(c.item))
        self.count_label.setText(f"{visible} 个媒体 · 当前筛选：{self._filter}")

    # ------------------------------------------------------------- selection
    def _on_selection(self, item: MediaItem, checked: bool) -> None:
        if checked:
            self._selected.add(item.name)
        else:
            self._selected.discard(item.name)
        self._update_bar()

    def _update_bar(self) -> None:
        chosen = [i for i in self.items if i.name in self._selected and i.name not in self._cleaned]
        total = sum(i.size for i in chosen)
        self.sel_label.setText(f"已选择 {len(chosen)} 项 · {human_size(total) if chosen else '0 B'}")
        self.btn_clean.setEnabled(bool(chosen))

    def _select_cleanable(self) -> None:
        for name, card in self._cards.items():
            if self._match(card.item) and card.item.cleanable and name not in self._cleaned:
                card.set_selected(True)
                self._selected.add(name)
        self._update_bar()

    # ------------------------------------------------------------- actions
    def _build_action_bar(self) -> QWidget:
        card = SectionCard("清理", "演示模式：只会改变界面状态，不会删除真实文件", FIF.BROOM)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.sel_label = StrongBodyLabel("已选择 0 项 · 0 B", card)
        row.addWidget(self.sel_label)
        row.addStretch(1)
        self.btn_clean = GradientButton("清理选中", card)
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._clean_selected)
        row.addWidget(self.btn_clean)
        card.content_layout.addLayout(row)
        return card

    def _clean_selected(self) -> None:
        chosen = [i for i in self.items if i.name in self._selected and i.name not in self._cleaned]
        cleanable = [i for i in chosen if i.cleanable]
        if not cleanable:
            InfoBar.warning("没有可清理项", "选中的媒体里没有截图、重复或缓存项", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=2600)
            return
        total = sum(i.size for i in cleanable)
        box = MessageBox(
            "确认清理",
            f"将清理 {len(cleanable)} 项，预计释放 {human_size(total)}。\n\n"
            "演示模式不会删除真实文件；正式版会先移到回收站并二次确认。",
            self,
        )
        box.yesButton.setText("清理")
        box.cancelButton.setText("取消")
        if not box.exec():
            return
        for item in cleanable:
            self._cleaned.add(item.name)
            self._selected.discard(item.name)
            card = self._cards.get(item.name)
            if card is not None:
                card.mark_cleaned()
        self._update_stats()
        self._apply_filter()
        self._update_bar()
        InfoBar.success("清理完成（演示）", f"已标记 {len(cleanable)} 项，释放约 {human_size(total)}",
                        parent=self, position=InfoBarPosition.TOP_RIGHT, duration=3000)

    def _clean_one(self, item: MediaItem) -> None:
        if not item.cleanable or item.name in self._cleaned:
            InfoBar.info("无需清理", "这个文件不在可清理范围内", parent=self,
                         position=InfoBarPosition.TOP_RIGHT, duration=2200)
            return
        self._cleaned.add(item.name)
        self._selected.discard(item.name)
        card = self._cards.get(item.name)
        if card is not None:
            card.mark_cleaned()
        self._update_stats()
        self._apply_filter()
        self._update_bar()
        InfoBar.success("已标记清理（演示）", item.name, parent=self,
                        position=InfoBarPosition.TOP_RIGHT, duration=2500)

    def _open_preview(self, item: MediaItem) -> None:
        dialog = MediaPreviewDialog(item, self.window())
        dialog.clean_requested.connect(self._clean_one)
        dialog.exec()

    def _scan(self) -> None:
        InfoBar.success(
            "扫描完成（演示）",
            f"找到 {len(self.items)} 个媒体文件，共 {human_size(sum(i.size for i in self.items))}",
            parent=self, position=InfoBarPosition.TOP_RIGHT, duration=2800,
        )

    # ------------------------------------------------------------- stats
    def _update_stats(self) -> None:
        photos = sum(1 for i in self.items if i.kind == "照片")
        videos = sum(1 for i in self.items if i.kind == "视频")
        total = sum(i.size for i in self.items)
        clean = sum(i.size for i in self.items if i.cleanable and i.name not in self._cleaned)
        self.stat_photos.set_value(str(photos), "演示数据 · 含微信图片")
        self.stat_videos.set_value(str(videos), "演示数据 · 含航拍")
        self.stat_total.set_value(human_size(total), "照片 + 视频")
        self.stat_clean.set_value(human_size(clean), "截图 / 重复 / 缓存")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._relayout_columns()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_columns()

    def _relayout_columns(self) -> None:
        window = self.window()
        available = (window.width() if window is not None else self.width()) - 196 - 44
        columns = max(2, min(5, available // 250))
        if columns != self._columns:
            self._columns = columns
            self._rebuild_grid()
