"""用 QtPdf 渲染 PDF 页面（需要在有 QGuiApplication 的进程中调用）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSizeF
from PySide6.QtPdf import QPdfDocument


def render_pages(src: str, dpi: int = 150, fmt: str = "png", password: str = "",
                 quality: int = 85, out_dir: str | None = None,
                 progress=None) -> list[str]:
    """把 PDF 每页渲染成图片，返回文件路径列表。

    out_dir 为空时写入系统临时目录下的子目录。
    """
    import tempfile

    doc = QPdfDocument()
    if password:
        doc.setPassword(password)
    error = doc.load(str(src))
    if error != QPdfDocument.Error.None_:
        raise RuntimeError(f"无法加载 PDF（错误码 {error}）")

    count = doc.pageCount()
    target_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="sc_pdf_"))
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(src).stem
    scale = max(0.2, float(dpi) / 72.0)
    outputs: list[str] = []
    for index in range(count):
        point = doc.pagePointSize(index)
        size = QSizeF(point.width() * scale, point.height() * scale).toSize()
        image = doc.render(index, size)
        if image.isNull():
            continue
        dest = target_dir / f"{stem}_{index + 1:03d}.{fmt}"
        if fmt.lower() in ("jpg", "jpeg"):
            image.save(str(dest), "JPG", quality)
        else:
            image.save(str(dest), "PNG")
        outputs.append(str(dest))
        if progress:
            progress(index + 1, count)
    doc.close()
    return outputs
