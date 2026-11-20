"""PDF 工具箱：合并 / 拆分 / 压缩 / 加解密 / 转图片 / 加水印 / 提取文本。

依赖 pypdf（页面操作）+ reportlab（生成水印与图片型 PDF）+ QtPdf（渲染页面）。
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions

from .pdf_render import render_pages  # noqa: F401  (对外暴露，供界面调用)


class PdfError(Exception):
    pass


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def describe_kind(path: str) -> str:
    """粗略判断文件类型，用于给出人话提示。"""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return "missing"
    suffix = p.suffix.lower()
    try:
        with open(p, "rb") as fh:
            head = fh.read(1024)
    except OSError:
        return "unreadable"
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"\x89PNG"):
        return "png"
    if head[:2] == b"\xff\xd8":
        return "jpeg"
    if head[:2] == b"BM":
        return "bmp"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:4] == b"GIF8":
        return "gif"
    if suffix in IMAGE_EXTS:
        return "image"
    if suffix == ".pdf":
        return "broken_pdf"
    return "unknown"


KIND_LABEL = {
    "pdf": "PDF 文件", "png": "PNG 图片", "jpeg": "JPEG 图片", "bmp": "BMP 图片",
    "webp": "WEBP 图片", "gif": "GIF 图片", "image": "图片", "unknown": "未知类型",
    "missing": "文件不存在", "unreadable": "无法读取", "broken_pdf": "损坏的 PDF",
}


def ensure_pdf(path: str) -> None:
    """确认是有效 PDF，否则抛出人话错误。"""
    if not path:
        raise PdfError("请先选择文件")
    kind = describe_kind(path)
    if kind == "missing":
        raise PdfError(f"文件不存在：{path}")
    if kind == "unreadable":
        raise PdfError("文件无法读取，可能被其他程序占用或权限不足")
    if kind in IMAGE_EXTS or kind in ("png", "jpeg", "bmp", "webp", "gif", "image"):
        raise PdfError(
            f"这是 {KIND_LABEL.get(kind, '图片')}，不是 PDF。"
            "想把多张图片合成一个 PDF，请改用左边的「图片转 PDF」"
        )
    if kind == "broken_pdf":
        raise PdfError("文件内容不是有效的 PDF，可能已损坏或后缀名被改过")
    if kind != "pdf":
        raise PdfError(f"这不是 PDF 文件（检测为 {KIND_LABEL.get(kind, '未知类型')}）")


def ensure_images(paths: list[str]) -> None:
    if not paths:
        raise PdfError("请先添加图片")
    for path in paths:
        kind = describe_kind(path)
        if kind == "missing":
            raise PdfError(f"文件不存在：{path}")
        if kind not in ("png", "jpeg", "bmp", "webp", "gif", "image"):
            raise PdfError(
                f"{Path(path).name} 不是图片（检测为 {KIND_LABEL.get(kind, '未知类型')}），"
                "请改用「合并 PDF」或「提取页面」等 PDF 功能"
            )


@dataclass
class PdfInfo:
    path: str
    pages: int = 0
    encrypted: bool = False
    title: str = ""
    author: str = ""
    producer: str = ""
    size: int = 0
    page_sizes: list[tuple[float, float]] = None


def read_info(path: str, password: str = "") -> PdfInfo:
    p = Path(path)
    info = PdfInfo(path=str(p), size=p.stat().st_size if p.exists() else 0)
    ensure_pdf(path)
    try:
        reader = PdfReader(str(p))
        info.encrypted = bool(reader.is_encrypted)
        if info.encrypted:
            if not password:
                return info
            if reader.decrypt(password) == 0:
                raise PdfError("密码错误")
        info.pages = len(reader.pages)
        meta = reader.metadata or {}
        info.title = str(meta.get("/Title") or "")
        info.author = str(meta.get("/Author") or "")
        info.producer = str(meta.get("/Producer") or "")
        sizes = []
        for page in reader.pages[:20]:
            box = page.mediabox
            sizes.append((float(box.width), float(box.height)))
        info.page_sizes = sizes
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError(_friendly(exc)) from exc
    return info


def _open_reader(path: str, password: str = "") -> PdfReader:
    ensure_pdf(path)
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise PdfError(_friendly(exc)) from exc
    if reader.is_encrypted:
        if not password:
            raise PdfError("该 PDF 已加密，请先填写密码")
        if reader.decrypt(password) == 0:
            raise PdfError("密码错误")
    return reader


def _friendly(exc: Exception) -> str:
    """把库的英文异常翻译成能看懂的提示。"""
    text = str(exc) or exc.__class__.__name__
    low = text.lower()
    if "stream has ended" in low or "eof" in low or "not a pdf" in low:
        return "文件不是有效的 PDF，或文件已损坏"
    if "invalid pdf header" in low or "cannot find" in low and "startxref" in low:
        return "PDF 结构不完整，文件可能已损坏"
    if "password" in low or "decrypt" in low:
        return "PDF 已加密，请先填写密码"
    if "permission" in low or "denied" in low:
        return "没有权限读取该文件"
    return f"无法打开文件：{text}"


def parse_ranges(text: str, page_count: int) -> list[int]:
    """解析 "1-3,5,7-" 形式的页码，返回 0 基索引列表。"""
    text = (text or "").strip()
    if not text:
        return list(range(page_count))
    out: list[int] = []
    for chunk in text.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            left, _, right = chunk.partition("-")
            start = int(left) if left.strip() else 1
            end = int(right) if right.strip() else page_count
            if start > end:
                start, end = end, start
            out.extend(range(start - 1, end))
        else:
            out.append(int(chunk) - 1)
    return [i for i in out if 0 <= i < page_count]


# ---------------------------------------------------------------------------- 基本操作
def merge(paths: list[str], out: str) -> tuple[int, str]:
    if len(paths) < 2:
        raise PdfError("请至少选择两个 PDF 文件")
    writer = PdfWriter()
    pages = 0
    for path in paths:
        ensure_pdf(path)
        reader = _open_reader(path)
        for page in reader.pages:
            writer.add_page(page)
            pages += 1
    _write(writer, out)
    return pages, f"已合并 {len(paths)} 个文件，共 {pages} 页"


def extract_pages(src: str, ranges: str, out: str, password: str = "") -> tuple[int, str]:
    reader = _open_reader(src, password)
    indexes = parse_ranges(ranges, len(reader.pages))
    if not indexes:
        raise PdfError("页码范围无效")
    writer = PdfWriter()
    for i in indexes:
        writer.add_page(reader.pages[i])
    _write(writer, out)
    return len(indexes), f"已提取 {len(indexes)} 页"


def delete_pages(src: str, ranges: str, out: str, password: str = "") -> tuple[int, str]:
    reader = _open_reader(src, password)
    drop = set(parse_ranges(ranges, len(reader.pages)))
    keep = [i for i in range(len(reader.pages)) if i not in drop]
    if not keep:
        raise PdfError("不能删除全部页面")
    writer = PdfWriter()
    for i in keep:
        writer.add_page(reader.pages[i])
    _write(writer, out)
    return len(drop), f"已删除 {len(drop)} 页，剩余 {len(keep)} 页"


def split_each(src: str, out_dir: str, password: str = "") -> tuple[int, str]:
    reader = _open_reader(src, password)
    stem = Path(src).stem
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    total = len(reader.pages)
    width = max(2, len(str(total)))
    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        dest = Path(out_dir) / f"{stem}_{i:0{width}d}.pdf"
        _write(writer, str(dest))
    return total, f"已拆分为 {total} 个单页文件"


def rotate_pages(src: str, angle: int, ranges: str, out: str, password: str = "") -> tuple[int, str]:
    reader = _open_reader(src, password)
    indexes = parse_ranges(ranges, len(reader.pages))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in indexes:
            page.rotate(int(angle))
        writer.add_page(page)
    _write(writer, out)
    return len(indexes), f"已旋转 {len(indexes)} 页"


def compress(src: str, out: str, mode: str = "lossless",
             dpi: int = 110, password: str = "") -> tuple[int, str]:
    """mode=lossless 保留文字；mode=image 渲染成图片后重建，体积更小但文字不可选。"""
    if mode == "image":
        return _compress_to_images(src, out, dpi, password)
    reader = _open_reader(src, password)
    writer = PdfWriter()
    for page in reader.pages:
        try:
            page.compress_content_streams(level=9)
        except Exception:
            pass
        writer.add_page(page)
    if reader.metadata:
        try:
            writer.add_metadata({k: v for k, v in reader.metadata.items() if isinstance(v, str)})
        except Exception:
            pass
    _write(writer, out)
    before = Path(src).stat().st_size
    after = Path(out).stat().st_size
    saved = (1 - after / before) * 100 if before else 0
    return len(reader.pages), f"无损优化完成：{_size(before)} → {_size(after)}（{saved:+.1f}%）"


def _compress_to_images(src: str, out: str, dpi: int, password: str = "") -> tuple[int, str]:
    images = render_pages(src, dpi=dpi, fmt="jpg", password=password, quality=60)
    if not images:
        raise PdfError("渲染页面失败")
    images_to_pdf(images, out)
    before = Path(src).stat().st_size
    after = Path(out).stat().st_size
    saved = (1 - after / before) * 100 if before else 0
    if after >= before:
        return len(images), (
            f"图片化后体积反而变大（{_size(before)} → {_size(after)}）："
            "该 PDF 文字为主、体积本来就小，建议改用「无损优化」"
        )
    return len(images), f"图片化压缩完成：{_size(before)} → {_size(after)}（{saved:+.1f}%）"


def encrypt(src: str, out: str, user_password: str, owner_password: str = "",
            allow_print: bool = True, allow_copy: bool = True) -> tuple[int, str]:
    if not user_password:
        raise PdfError("请输入打开密码")
    reader = _open_reader(src)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    perms = UserAccessPermissions.PRINT if allow_print else UserAccessPermissions(0)
    if allow_copy:
        perms |= UserAccessPermissions.EXTRACT
    writer.encrypt(user_password=user_password,
                   owner_password=owner_password or user_password,
                   permissions_flag=perms)
    _write(writer, out)
    return len(reader.pages), "已加密，打开时需要输入密码"


def decrypt(src: str, out: str, password: str) -> tuple[int, str]:
    reader = _open_reader(src, password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    _write(writer, out)
    return len(reader.pages), "已解除密码保护"


def extract_text(src: str, password: str = "") -> tuple[str, int]:
    reader = _open_reader(src, password)
    chunks = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        chunks.append(f"──── 第 {i} 页 ────\n{text.strip()}")
    return "\n\n".join(chunks), len(reader.pages)


def add_watermark(src: str, out: str, text: str, opacity: float = 0.15,
                  font_size: int = 48, angle: int = 45, password: str = "") -> tuple[int, str]:
    from reportlab.lib.colors import Color
    from reportlab.pdfgen import canvas as rl_canvas

    reader = _open_reader(src, password)
    writer = PdfWriter(clone_from=reader)
    overlay_cache: dict[tuple[int, int], PdfReader] = {}
    for page in writer.pages:
        box = page.mediabox
        w, h = float(box.width), float(box.height)
        key = (int(w), int(h))
        if key not in overlay_cache:
            buf = io.BytesIO()
            c = rl_canvas.Canvas(buf, pagesize=(w, h))
            c.saveState()
            c.setFillColor(Color(0.55, 0.55, 0.55, alpha=opacity))
            c.setFont("Helvetica-Bold", font_size)
            c.translate(w / 2, h / 2)
            c.rotate(angle)
            c.drawCentredString(0, 0, text)
            c.restoreState()
            c.save()
            buf.seek(0)
            overlay_cache[key] = PdfReader(buf)
        overlay = overlay_cache[key].pages[0]
        page.merge_page(overlay)
    _write(writer, out)
    return len(reader.pages), f"已为 {len(reader.pages)} 页添加水印"


def images_to_pdf(paths: list[str], out: str) -> tuple[int, str]:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas

    if not paths:
        raise PdfError("请选择至少一张图片")
    valid = [p for p in paths if Path(p).is_file()]
    if not valid:
        raise PdfError("所选文件都不存在")
    ensure_images(valid)
    first = ImageReader(valid[0])
    iw, ih = first.getSize()
    c = rl_canvas.Canvas(out, pagesize=(iw, ih))
    count = 0
    for path in valid:
        try:
            img = ImageReader(path)
            w, h = img.getSize()
        except Exception:
            continue
        c.setPageSize((w, h))
        c.drawImage(img, 0, 0, width=w, height=h)
        c.showPage()
        count += 1
    c.save()
    if count == 0:
        raise PdfError("没有可用的图片")
    return count, f"已生成 {count} 页 PDF"


def _write(writer: PdfWriter, out: str) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out, "wb") as fh:
            writer.write(fh)
    except PermissionError as exc:
        raise PdfError(f"无法写入文件（可能被其他程序占用）：{out}") from exc
    except Exception as exc:
        raise PdfError(f"写入失败：{exc}") from exc


def _size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def unique_path(base: str) -> str:
    """避免覆盖已有文件。"""
    p = Path(base)
    if not p.exists():
        return str(p)
    for i in range(1, 999):
        candidate = p.with_name(f"{p.stem}_{i}{p.suffix}")
        if not candidate.exists():
            return str(candidate)
    return str(p)
