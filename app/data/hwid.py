"""本机机器码。

使用 MachineGuid + 系统盘卷序列号 + CPU 标识生成稳定指纹，
只做授权绑定用途，不读取也不修改任何设备枚举信息。
"""
from __future__ import annotations

import hashlib
import os
import platform
import socket
import winreg


def _machine_guid() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as h:
            return str(winreg.QueryValueEx(h, "MachineGuid")[0])
    except OSError:
        return ""


def _volume_serial(drive: str = "C:\\") -> str:
    try:
        import ctypes
        serial = ctypes.c_ulong(0)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive), None, 0,
            ctypes.byref(serial), None, None, None, 0,
        )
        return f"{serial.value:08X}"
    except Exception:
        return ""


def machine_code() -> str:
    raw = "|".join([
        _machine_guid(),
        _volume_serial(),
        platform.machine(),
        os.environ.get("PROCESSOR_IDENTIFIER", ""),
    ])
    digest = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest().upper()
    body = digest[:16]
    return "-".join(body[i:i + 4] for i in range(0, 16, 4))


def machine_name() -> str:
    return socket.gethostname()


def user_name() -> str:
    return os.environ.get("USERNAME", "")
