"""程序入口。"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from . import APP_NAME, APP_TITLE, APP_VERSION
from .core.paths import LOG_PATH, ensure_app_dirs
from .state import state


def _install_excepthook() -> None:
    """把未捕获异常写进日志并弹窗，避免单文件 exe 出错后毫无反应。"""

    def hook(exc_type, exc, tb) -> None:
        try:
            ensure_app_dirs()
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {exc_type.__name__}: {exc}\n")
                traceback.print_exception(exc_type, exc, tb, file=fh)
        except Exception:
            pass
        try:
            if QApplication.instance() is not None:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None, APP_TITLE,
                    f"程序发生错误：\n\n{exc_type.__name__}: {exc}\n\n"
                    f"详细信息已记录到：\n{LOG_PATH}",
                )
        except Exception:
            pass

    sys.excepthook = hook


def _run_selftest() -> int:
    """命令行自检：`Windows maintain.exe --selftest`

    结果写入数据目录的 selftest.txt。
    单文件 exe 没有控制台，所以不打印到屏幕，客户把文件发回来即可。
    """
    import tempfile
    from pathlib import Path

    ensure_app_dirs()
    lines = [f"{APP_TITLE} v{APP_VERSION} 自检", "-" * 44]
    ok = True
    try:
        tmp = Path(tempfile.mkdtemp(prefix="wm_selftest_"))

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl_canvas
        sample = tmp / "sample.pdf"
        c = rl_canvas.Canvas(str(sample), pagesize=A4)
        c.setFont("Helvetica", 24)
        c.drawString(80, 700, "Windows maintain selftest")
        c.showPage()
        c.save()
        lines.append(f"[OK] reportlab 生成 PDF：{sample.stat().st_size} 字节")

        from .core import pdfkit
        info = pdfkit.read_info(str(sample))
        lines.append(f"[OK] pypdf 解析：{info.pages} 页，未加密={not info.encrypted}")

        marked = tmp / "marked.pdf"
        pdfkit.add_watermark(str(sample), str(marked), "自检水印")
        lines.append(f"[OK] 添加水印（依赖 reportlab）：{marked.stat().st_size} 字节")

        merged = tmp / "merged.pdf"
        pdfkit.merge([str(sample), str(marked)], str(merged))
        lines.append(f"[OK] 合并 PDF：{pdfkit.read_info(str(merged)).pages} 页")

        enc = tmp / "enc.pdf"
        pdfkit.encrypt(str(sample), str(enc), "abc123")
        lines.append(f"[OK] 加密 PDF：{'已加密' if pdfkit.read_info(str(enc)).encrypted else '未加密'}")

        text, pages = pdfkit.extract_text(str(sample))
        lines.append(f"[OK] 提取文字：{pages} 页，命中关键字={'Windows maintain' in text}")
    except Exception as exc:
        ok = False
        lines.append(f"[失败] {type(exc).__name__}: {exc}")

    # Qt 相关（渲染）需要 QGuiApplication
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([sys.argv[0]])
        from .core.pdf_render import render_pages
        tmp2 = Path(tempfile.mkdtemp(prefix="wm_selftest_q_"))
        sample2 = tmp2 / "r.pdf"
        from reportlab.pdfgen import canvas as rl2
        c2 = rl2.Canvas(str(sample2), pagesize=A4)
        c2.drawString(80, 700, "render test")
        c2.showPage()
        c2.save()
        files = render_pages(str(sample2), dpi=72, out_dir=str(tmp2 / "out"))
        lines.append(f"[OK] QtPdf 渲染页面为图片：{len(files)} 张")
        del app
    except Exception as exc:
        ok = False
        lines.append(f"[失败] QtPdf 渲染：{type(exc).__name__}: {exc}")

    try:
        from .core.items import ITEMS
        from .core import hardware
        lines.append(f"[OK] 清理项加载：{len(ITEMS)} 项")
        data = hardware.collect()
        lines.append(f"[OK] 硬件采集：CIM={'成功' if data.get('ok') else '回退模式'}"
                     f"，内存条 {len(data.get('memory') or [])} 条"
                     f"，显卡 {len(data.get('gpu') or [])} 个")
    except Exception as exc:
        ok = False
        lines.append(f"[失败] 硬件采集：{type(exc).__name__}: {exc}")

    lines.append("-" * 44)
    lines.append("全部通过" if ok else "存在失败项，请把本文件发给客服")
    result_path = LOG_PATH.parent / "selftest.txt"
    try:
        result_path.write_text("\n".join(lines), encoding="utf-8-sig")
    except Exception:
        pass
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return _run_selftest()

    ensure_app_dirs()
    _install_excepthook()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont("Microsoft YaHei UI", 10))

    from .ui.theme import apply_theme
    apply_theme(state.theme_mode)

    from .ui.window import MainWindow
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
