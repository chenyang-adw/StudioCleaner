"""演示数据：只用于 UI 预览，不参与真实文件操作。"""
from __future__ import annotations

from dataclasses import dataclass

from .core.items import CleanItem, RISK_NORMAL, RISK_SAFE

GB = 1024 ** 3
MB = 1024 ** 2


@dataclass(frozen=True)
class MediaItem:
    name: str
    kind: str
    width: int
    height: int
    size: int
    date: str
    folder: str
    c1: str
    c2: str
    duration: str = ""
    cleanable: bool = False
    duplicate: bool = False
    reason: str = ""


MEDIA_ITEMS: list[MediaItem] = [
    MediaItem("IMG_20261118_142233.jpg", "照片", 4032, 3024, 4_823_040, "2026-11-18", "图片/2026", "#F59E0B", "#EF4444"),
    MediaItem("IMG_20261118_142257.jpg", "照片", 4032, 3024, 4_718_592, "2026-11-18", "图片/2026", "#F97316", "#DB2777"),
    MediaItem("VID_20261112_190455.mp4", "视频", 1920, 1080, 428_867_584, "2026-11-12", "视频/旅行", "#0EA5E9", "#4C6FFF", "03:42"),
    MediaItem("Screenshot_2026-11-20_163012.png", "截图", 2560, 1600, 2_097_152, "2026-11-20", "图片/截图", "#64748B", "#334155", cleanable=True, reason="截图"),
    MediaItem("微信图片_20261119_101522.jpg", "照片", 1280, 1706, 2_306_867, "2026-11-19", "图片/微信", "#10B981", "#0F766E"),
    MediaItem("DJI_20261115_093012.mp4", "视频", 3840, 2160, 1_288_490_188, "2026-11-15", "视频/航拍", "#8B5CF6", "#4C6FFF", "01:28"),
    MediaItem("Screenshot_2026-11-19_221145.png", "截图", 2560, 1600, 1_887_437, "2026-11-19", "图片/截图", "#475569", "#1E293B", cleanable=True, reason="截图"),
    MediaItem("IMG_20261117_081530.jpg", "照片", 4032, 3024, 5_138_432, "2026-11-17", "图片/2026", "#F43F5E", "#F59E0B"),
    MediaItem("IMG_20261117_081530 (1).jpg", "照片", 4032, 3024, 5_138_432, "2026-11-17", "图片/2026", "#F43F5E", "#F59E0B", cleanable=True, duplicate=True, reason="重复照片"),
    MediaItem("VID_20261108_201022.mp4", "视频", 1920, 1080, 86_509_158, "2026-11-08", "视频/日常", "#06B6D4", "#0891B2", "00:47"),
    MediaItem("IMG_20261106_155501.jpg", "照片", 3024, 4032, 3_355_443, "2026-11-06", "图片/2026", "#84CC16", "#16A34A"),
    MediaItem("Screenshot_2026-11-18_094210.png", "截图", 1920, 1080, 1_258_291, "2026-11-18", "图片/截图", "#64748B", "#334155", cleanable=True, reason="截图"),
    MediaItem("VID_20261103_174512.mp4", "视频", 1920, 1080, 240_123_904, "2026-11-03", "视频/日常", "#F59E0B", "#B45309", "02:11"),
    MediaItem("微信图片_20261102_193310.jpg", "照片", 1080, 1440, 1_887_437, "2026-11-02", "图片/微信", "#14B8A6", "#0F766E"),
    MediaItem("IMG_20261030_120233.jpg", "照片", 4032, 3024, 6_291_456, "2026-10-30", "图片/2026", "#EC4899", "#8B5CF6"),
    MediaItem("VID_20261028_162044.mp4", "视频", 1280, 720, 64_487_424, "2026-10-28", "视频/日常", "#3B82F6", "#1D4ED8", "00:36"),
    MediaItem("Screenshot_2026-10-26_112233.png", "截图", 2560, 1600, 2_411_724, "2026-10-26", "图片/截图", "#475569", "#1E293B", cleanable=True, reason="截图"),
    MediaItem("IMG_20261025_174510.jpg", "照片", 3024, 4032, 3_774_873, "2026-10-25", "图片/2026", "#A855F7", "#6366F1"),
    MediaItem("IMG_20261025_174510 (1).jpg", "照片", 3024, 4032, 3_774_873, "2026-10-25", "图片/2026", "#A855F7", "#6366F1", cleanable=True, duplicate=True, reason="重复照片"),
    MediaItem("DJI_20261022_075512.mp4", "视频", 3840, 2160, 892_338_176, "2026-10-22", "视频/航拍", "#0EA5E9", "#7C3AED", "01:05"),
    MediaItem("IMG_20261020_093344.jpg", "照片", 4032, 3024, 4_194_304, "2026-10-20", "图片/2026", "#F97316", "#DC2626"),
    MediaItem("微信图片_20261019_204455.jpg", "照片", 1280, 1706, 2_516_582, "2026-10-19", "图片/微信", "#22C55E", "#15803D"),
    MediaItem("VID_20261015_131122.mp4", "视频", 1920, 1080, 156_237_824, "2026-10-15", "视频/日常", "#0891B2", "#155E75", "01:19"),
    MediaItem("Screenshot_2026-10-12_155501.png", "截图", 1920, 1080, 943_718, "2026-10-12", "图片/截图", "#64748B", "#334155", cleanable=True, reason="截图"),
]


SPACE_TREE: list[dict] = [
    {
        "name": "Users", "size": 58 * GB, "color": "#4C6FFF",
        "children": [
            {"name": "Pictures", "size": 18 * GB, "color": "#F59E0B"},
            {"name": "Videos", "size": 22 * GB, "color": "#8B5CF6"},
            {"name": "AppData", "size": 12 * GB, "color": "#0EA5E9"},
            {"name": "Documents", "size": 6 * GB, "color": "#10B981"},
        ],
    },
    {
        "name": "Windows", "size": 42 * GB, "color": "#64748B",
        "children": [
            {"name": "WinSxS", "size": 18 * GB, "color": "#475569"},
            {"name": "System32", "size": 12 * GB, "color": "#334155"},
            {"name": "Logs", "size": 7 * GB, "color": "#94A3B8"},
            {"name": "Temp", "size": 5 * GB, "color": "#CBD5E1"},
        ],
    },
    {
        "name": "Program Files", "size": 31 * GB, "color": "#10B981",
        "children": [
            {"name": "Adobe", "size": 12 * GB, "color": "#059669"},
            {"name": "Microsoft", "size": 9 * GB, "color": "#047857"},
            {"name": "其他", "size": 10 * GB, "color": "#34D399"},
        ],
    },
    {
        "name": "Games", "size": 24 * GB, "color": "#F43F5E",
        "children": [
            {"name": "Steam", "size": 16 * GB, "color": "#E11D48"},
            {"name": "其他", "size": 8 * GB, "color": "#FB7185"},
        ],
    },
    {
        "name": "ProgramData", "size": 12 * GB, "color": "#F59E0B",
        "children": [
            {"name": "Package Cache", "size": 6 * GB, "color": "#D97706"},
            {"name": "其他", "size": 6 * GB, "color": "#FBBF24"},
        ],
    },
    {"name": "其他", "size": 8 * GB, "color": "#94A3B8"},
]


def _space_history() -> list[tuple[str, float]]:
    labels = [f"10-{d}" for d in range(22, 32)] + [f"11-{d}" for d in range(1, 21)]
    return [(label, 108.4 + i * 0.78 + (i % 4) * 0.22) for i, label in enumerate(labels)]


SPACE_HISTORY = _space_history()


DUPLICATE_GROUPS = [
    {
        "name": "IMG_20261117_081530.jpg", "kind": "照片", "size": 5_138_432,
        "copies": [
            ("C:\\Users\\Demo\\Pictures\\2026\\IMG_20261117_081530.jpg", "2026-11-17 08:15"),
            ("C:\\Users\\Demo\\Pictures\\2026\\IMG_20261117_081530 (1).jpg", "2026-11-17 08:16"),
            ("C:\\Users\\Demo\\Downloads\\IMG_20261117_081530.jpg", "2026-11-17 09:02"),
        ],
        "c1": "#F43F5E", "c2": "#F59E0B",
    },
    {
        "name": "DJI_20261022_075512.mp4", "kind": "视频", "size": 892_338_176,
        "copies": [
            ("D:\\Videos\\航拍\\DJI_20261022_075512.mp4", "2026-10-22 07:55"),
            ("D:\\Videos\\备份\\DJI_20261022_075512.mp4", "2026-10-22 08:01"),
        ],
        "c1": "#0EA5E9", "c2": "#7C3AED",
    },
    {
        "name": "微信图片_20261019_204455.jpg", "kind": "照片", "size": 2_516_582,
        "copies": [
            ("C:\\Users\\Demo\\Pictures\\微信\\微信图片_20261019_204455.jpg", "2026-10-19 20:44"),
            ("C:\\Users\\Demo\\Downloads\\微信图片_20261019_204455.jpg", "2026-10-19 20:45"),
        ],
        "c1": "#22C55E", "c2": "#15803D",
    },
    {
        "name": "Screenshot_2026-10-26_112233.png", "kind": "截图", "size": 2_411_724,
        "copies": [
            ("C:\\Users\\Demo\\Pictures\\截图\\Screenshot_2026-10-26_112233.png", "2026-10-26 11:22"),
            ("C:\\Users\\Demo\\Desktop\\Screenshot_2026-10-26_112233.png", "2026-10-26 11:23"),
        ],
        "c1": "#475569", "c2": "#1E293B",
    },
]


STARTUP_ITEMS = [
    {"name": "ChatGPT", "desc": "OpenAI · 开机启动", "type": "注册表", "enabled": True, "impact": "高", "path": "HKCU\\...\\Run\\ChatGPT"},
    {"name": "Doubao Launcher", "desc": "豆包桌面端 · 开机启动", "type": "注册表", "enabled": True, "impact": "中", "path": "HKCU\\...\\Run\\Doubao"},
    {"name": "Microsoft Edge", "desc": "Microsoft Corporation · 启动增强", "type": "注册表", "enabled": True, "impact": "中", "path": "HKLM\\...\\Run\\MicrosoftEdgeAutoLaunch"},
    {"name": "微信", "desc": "腾讯 · 开机启动", "type": "注册表", "enabled": True, "impact": "高", "path": "HKCU\\...\\Run\\WeChat"},
    {"name": "QQ", "desc": "腾讯 · 开机启动", "type": "注册表", "enabled": True, "impact": "高", "path": "HKCU\\...\\Run\\QQ"},
    {"name": "AMD Crash Defender Service", "desc": "AMD · 显卡崩溃守护", "type": "服务", "enabled": True, "impact": "低", "path": "AMD Crash Defender Service"},
    {"name": "BaiduNetdiskUtility", "desc": "百度网盘 · 空闲时申请磁盘空间", "type": "服务", "enabled": False, "impact": "低", "path": "BaiduNetdiskUtility"},
    {"name": "Docker Desktop", "desc": "Docker · 登录时启动", "type": "注册表", "enabled": False, "impact": "高", "path": "HKCU\\...\\Run\\Docker Desktop"},
    {"name": "OneDrive", "desc": "Microsoft · 文件同步", "type": "计划任务", "enabled": True, "impact": "中", "path": "\\Microsoft\\OneDrive\\OneDrive Standalone Update Task"},
    {"name": "Adobe Updater", "desc": "Adobe · 更新检查", "type": "计划任务", "enabled": True, "impact": "低", "path": "\\Adobe\\Adobe Acrobat Update Task"},
    {"name": "Steam Client Bootstrapper", "desc": "Valve · 登录时启动", "type": "启动文件夹", "enabled": False, "impact": "中", "path": "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Steam.lnk"},
    {"name": "残留项：旧版迅雷", "desc": "指向不存在的程序", "type": "残留", "enabled": False, "impact": "低", "path": "HKCU\\...\\Run\\Thunder"},
]


MAINTENANCE_ACTIONS = [
    {"title": "修复 Windows 系统文件", "desc": "使用 sfc /scannow 检查并修复损坏的系统文件。", "icon": "SYNC", "category": "系统修复", "admin": True, "time": "3–10 分钟"},
    {"title": "重建 Windows 搜索索引", "desc": "搜索不到文件或结果不正确时，重建索引。", "icon": "SEARCH", "category": "搜索与界面", "admin": True, "time": "5–20 分钟"},
    {"title": "重建图标和缩略图缓存", "desc": "修复图标空白、缩略图错误；会重启资源管理器。", "icon": "PHOTO", "category": "搜索与界面", "admin": False, "time": "1–2 分钟"},
    {"title": "重启 Windows 更新服务", "desc": "重新启动 wuauserv，并检查更新状态。", "icon": "SYNC", "category": "系统修复", "admin": True, "time": "30 秒"},
    {"title": "修复打印队列", "desc": "清空卡住的打印任务，并重启打印服务。", "icon": "PRINT", "category": "系统修复", "admin": True, "time": "30 秒"},
    {"title": "修复性能计数器", "desc": "重建性能计数器，修复任务管理器数值异常。", "icon": "SPEED_HIGH", "category": "系统修复", "admin": True, "time": "1 分钟"},
    {"title": "检查 Windows 系统盘", "desc": "只读检查文件系统错误，不中断当前操作。", "icon": "SAVE", "category": "系统修复", "admin": True, "time": "1–5 分钟"},
    {"title": "重启音频服务", "desc": "系统无声或音频设备无响应时重启 Audiosrv。", "icon": "MUSIC", "category": "系统修复", "admin": True, "time": "15 秒"},
    {"title": "重置 Microsoft Store 缓存", "desc": "清除商店缓存，解决打不开、下载卡住。", "icon": "SHOPPING_CART", "category": "系统修复", "admin": False, "time": "30 秒"},
    {"title": "刷新 DNS 缓存", "desc": "清除过期域名解析记录，解决网站打不开。", "icon": "GLOBE", "category": "网络连接", "admin": True, "time": "5 秒"},
    {"title": "重置 WinHTTP 代理", "desc": "清理 WinHTTP 代理设置，修复部分应用无法联网。", "icon": "WIFI", "category": "网络连接", "admin": True, "time": "10 秒"},
]


def demo_clean_items() -> list[CleanItem]:
    """三条演示规则，让清理页能看到新品类与进程阻断。"""

    def scan_dev():
        return 1284, 3_200_000_000

    def clean_dev(log):
        log("演示：清理 npm / pip / Cargo / Go 缓存")
        return {"removed": 1284, "freed": 3_200_000_000, "skipped": 0, "note": "演示模式"}

    def scan_ai():
        return 86, 1_100_000_000

    def clean_ai(log):
        log("演示：清理 ChatGPT / 豆包 / DeepSeek 缓存")
        return {"removed": 86, "freed": 1_100_000_000, "skipped": 0, "note": "演示模式"}

    def scan_project():
        return 12, 4_800_000_000

    def clean_project(log):
        log("演示：清理 3 个项目内的 node_modules / target / build")
        return {"removed": 12, "freed": 4_800_000_000, "skipped": 0, "note": "演示模式"}

    return [
        CleanItem(
            "demo_dev_cache", "开发者缓存",
            "npm / pnpm / pip / uv / Cargo / Go / Gradle / Maven 等",
            "开发缓存", RISK_SAFE, False, True, scan_dev, clean_dev,
        ),
        CleanItem(
            "demo_ai_cache", "AI 工具缓存",
            "ChatGPT / 豆包 / DeepSeek / WorkBuddy 的缓存与日志",
            "AI 工具", RISK_NORMAL, False, True, scan_ai, clean_ai,
            blocked_by=("ChatGPT.exe", "Doubao.exe", "DeepSeek Harness.exe"),
        ),
        CleanItem(
            "demo_project_artifacts", "项目构建产物",
            "项目根内的 node_modules / target / build / .venv / __pycache__",
            "项目产物", RISK_NORMAL, False, False, scan_project, clean_project,
        ),
    ]

