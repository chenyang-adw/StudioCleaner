"""主题与配色：以浅色渐变为主，深色作为可选项。"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, qconfig, setTheme, setThemeColor

ACCENT = "#4C6FFF"
ACCENT_2 = "#8B5CF6"
ACCENT_HOVER = "#3D5CE5"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"
INFO = "#0891B2"

CATEGORY_COLORS = {
    "系统缓存": "#4C6FFF",
    "浏览器": "#16A34A",
    "网络": "#0891B2",
    "系统维护": "#D97706",
}

RADIUS = {"sm": 8, "md": 12, "lg": 16, "xl": 20}

_MODE_MAP = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}


def apply_theme(mode: str = "light") -> None:
    setTheme(_MODE_MAP.get(mode, Theme.LIGHT))
    setThemeColor(QColor(ACCENT))
    _apply_app_palette()


def _apply_app_palette() -> None:
    """Fluent 卡片是半透明的，若 Qt 跟随系统深色会给滚动区深色底，导致卡片发暗。
    这里把应用调色板显式对齐到我们自己的配色。"""
    app = QApplication.instance()
    if app is None:
        return
    p = palette()
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(p["page_from"]))
    pal.setColor(QPalette.WindowText, QColor(p["text"]))
    pal.setColor(QPalette.Base, QColor(p["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor(p["surface_2"]))
    pal.setColor(QPalette.Text, QColor(p["text"]))
    pal.setColor(QPalette.Button, QColor(p["btn_bg"]))
    pal.setColor(QPalette.ButtonText, QColor(p["btn_fg"]))
    pal.setColor(QPalette.Highlight, QColor(p["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, QColor(p["surface"]))
    pal.setColor(QPalette.ToolTipText, QColor(p["text"]))
    pal.setColor(QPalette.PlaceholderText, QColor(p["muted"]))
    app.setPalette(pal)


def is_dark() -> bool:
    try:
        return qconfig.theme == Theme.DARK
    except Exception:
        return False


def palette() -> dict:
    """浅色为主的设计令牌。"""
    if is_dark():
        return {
            "page_from": "#171A21",
            "page_to": "#1D2029",
            "surface": "#20242E",
            "surface_2": "#262B36",
            "border": "#313747",
            "text": "#F1F4F9",
            "sub": "#98A1B3",
            "muted": "#6E7788",
            "accent": "#7C93FF",
            "accent_2": "#A98BFF",
            "success": "#4ADE80",
            "warning": "#FBBF24",
            "danger": "#F87171",
            "info": "#38BDF8",
            "ring_track": "#2C3140",
            "hero_from": "#242B44",
            "hero_to": "#33284A",
            "hero_text": "#F1F4F9",
            "hero_sub": "#B4BCCC",
            "hero_chip_bg": "rgba(255,255,255,0.12)",
            "hero_chip_fg": "#E7EBF5",
            "hero_btn": "rgba(255,255,255,0.14)",
            "hero_btn_border": "rgba(255,255,255,0.28)",
            "hero_btn_fg": "#FFFFFF",
            "btn_bg": "#252A36",
            "btn_border": "#3A4152",
            "btn_fg": "#E7EBF5",
            "btn_hover": "#2E3442",
        }
    return {
        "page_from": "#F7F9FF",
        "page_to": "#EEF2FC",
        "surface": "#FFFFFF",
        "surface_2": "#F5F7FD",
        "border": "#E3E8F4",
        "text": "#1B2130",
        "sub": "#6B7690",
        "muted": "#98A1B5",
        "accent": "#4C6FFF",
        "accent_2": "#8B5CF6",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "info": "#0891B2",
        "ring_track": "#E6EBF7",
        "hero_from": "#EAF0FF",
        "hero_to": "#F4EBFF",
        "hero_text": "#1B2130",
        "hero_sub": "#5C6784",
        "hero_chip_bg": "rgba(255,255,255,0.75)",
        "hero_chip_fg": "#3A4463",
        "hero_btn": "rgba(255,255,255,0.85)",
        "hero_btn_border": "#D8E0F5",
        "hero_btn_fg": "#2A3350",
        "btn_bg": "#FFFFFF",
        "btn_border": "#DBE2F2",
        "btn_fg": "#2A3350",
        "btn_hover": "#F2F5FE",
    }


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, ACCENT)


# ---------------------------------------------------------------------------- 控件样式
def outline_button_qss() -> str:
    p = palette()
    return (
        "QPushButton{"
        f"background:{p['btn_bg']};color:{p['btn_fg']};"
        f"border:1px solid {p['btn_border']};border-radius:10px;"
        "padding:8px 16px;font-weight:600;}"
        f"QPushButton:hover{{background:{p['btn_hover']};border-color:{p['accent']}66;}}"
        f"QPushButton:pressed{{background:{p['surface_2']};}}"
        f"QPushButton:disabled{{color:{p['muted']};border-color:{p['border']};"
        f"background:{p['surface_2']};}}"
    )


def gradient_button_qss() -> str:
    p = palette()
    return (
        "QPushButton{"
        f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {p['accent']},stop:1 {p['accent_2']});"
        "color:#FFFFFF;border:none;border-radius:10px;"
        "padding:9px 18px;font-weight:600;}"
        "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {ACCENT_HOVER},stop:1 {p['accent_2']});}}"
        f"QPushButton:disabled{{background:{p['surface_2']};color:{p['muted']};}}"
    )


def soft_button_qss() -> str:
    p = palette()
    return (
        "QPushButton{"
        f"background:{p['surface_2']};color:{p['accent']};"
        f"border:1px solid {p['border']};border-radius:10px;"
        "padding:8px 14px;font-weight:600;}"
        f"QPushButton:hover{{background:{p['btn_hover']};border-color:{p['accent']}55;}}"
    )


def card_qss() -> str:
    p = palette()
    return (
        f"QFrame#Card{{background:{p['surface']};border:1px solid {p['border']};"
        "border-radius:14px;}}"
    )
