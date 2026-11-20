# -*- mode: python ; coding: utf-8 -*-
"""
单文件（onefile）打包配置：产出一个可以直接交付的 exe，用户只需要下载这一个文件。

两个关键点：
1. 必须排除第三方 ICU 动态库。Qt6Core 依赖 Windows 自带的免版本号 ICU
   （C:\\Windows\\System32\\icuuc.dll）；PyInstaller 若从 PATH 抓到第三方 ICU
   （如 poppler 的 icuuc.dll，只导出 ucnv_open_78 这类带版本号符号），
   打进包里会遮蔽系统 ICU，启动时报 "DLL load failed while importing QtGui: 找不到指定的程序"。
2. 单文件模式下 Qt 插件与 qfluentwidgets 资源都会被打进归档，运行时解压到临时目录。
"""
import os

from PyInstaller.utils.hooks import collect_all

qfw_datas, qfw_binaries, qfw_hidden = collect_all("qfluentwidgets")

EXCLUDES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtDesigner", "PySide6.QtTest",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtWebSockets",
    "PySide6.QtHelp",
    "tkinter", "unittest", "pydoc",
]

NEVER_BUNDLE = {
    "icuuc.dll", "icuin.dll", "icudt.dll", "icuio.dll", "icutu.dll", "icutest.dll",
    "icuuc78.dll", "icuin78.dll", "icudt78.dll", "icuio78.dll", "icutu78.dll",
    "icutest78.dll", "icuuc77.dll", "icuin77.dll", "icudt77.dll",
    "icuuc76.dll", "icuin76.dll", "icudt76.dll",
    "icuuc75.dll", "icuin75.dll", "icudt75.dll",
    "icuuc74.dll", "icuin74.dll", "icudt74.dll",
}

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=qfw_binaries,
    datas=qfw_datas,
    hiddenimports=qfw_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    # optimize=2 会让打包进去的字节码丢掉文档字符串与断言，反编译结果更难读
    optimize=2,
)

_dropped = [b for b in a.binaries if os.path.basename(b[0]).lower() in NEVER_BUNDLE]
a.binaries = [b for b in a.binaries if os.path.basename(b[0]).lower() not in NEVER_BUNDLE]
print("[spec] dropped third-party ICU:", [b[0] for b in _dropped])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="StudioCleaner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",
)
