"""
core/icons.py
-------------
Extração de ícones de executáveis via Windows Shell API (Shell32/GDI32).
Eliminando a duplicação que existia em NetPulse, SentinelAutorun e TaskGuard.
"""

import os
import struct
import base64
import ctypes
from ctypes import wintypes

from core.utils import resolve_path

# --- Constantes WinAPI ---
SHGFI_ICON      = 0x000000100
SHGFI_LARGEICON = 0x000000000
SHGFI_SMALLICON = 0x000000001


# --- Estruturas WinAPI ---
class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon",         wintypes.HICON),
        ("iIcon",         ctypes.c_int),
        ("dwAttributes",  wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName",    wintypes.WCHAR * 80),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon",    wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask",  wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType",       wintypes.LONG),
        ("bmWidth",      wintypes.LONG),
        ("bmHeight",     wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes",     wintypes.WORD),
        ("bmBitsPixel",  wintypes.WORD),
        ("bmBits",       wintypes.LPVOID),
    ]


# Cache global de ícones para evitar extrações repetidas
_icon_cache: dict[str, str] = {}


def get_icon_base64(raw_path: str) -> str:
    """
    Extrai o ícone de um executável e retorna como data URI base64 (BMP).
    Usa cache interno para evitar re-extrações.

    Args:
        raw_path: Caminho bruto do executável (pode conter aspas/argumentos).

    Returns:
        String "data:image/bmp;base64,..." ou "" se falhar.
    """
    clean_path = resolve_path(raw_path)
    if not clean_path or not os.path.exists(clean_path):
        return ""

    if clean_path in _icon_cache:
        return _icon_cache[clean_path]

    try:
        shfi = SHFILEINFOW()
        result = ctypes.windll.shell32.SHGetFileInfoW(
            clean_path, 0, ctypes.byref(shfi), ctypes.sizeof(shfi),
            SHGFI_ICON | SHGFI_LARGEICON
        )
        if not result or not shfi.hIcon:
            return ""

        # Obter dados do bitmap do ícone
        icon_info = ICONINFO()
        ctypes.windll.user32.GetIconInfo(shfi.hIcon, ctypes.byref(icon_info))

        bm = BITMAP()
        ctypes.windll.gdi32.GetObjectW(
            icon_info.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm)
        )

        width, height = bm.bmWidth, bm.bmHeight
        if width <= 0 or height <= 0:
            return ""

        pixel_data_size = width * height * 4
        bmi_header = struct.pack(
            '<IiiHHIIiiII', 40, width, height, 1, 32, 0,
            pixel_data_size, 0, 0, 0, 0
        )

        hdc = ctypes.windll.user32.GetDC(None)
        pixel_buf = ctypes.create_string_buffer(pixel_data_size)
        ctypes.windll.gdi32.GetDIBits(
            hdc, icon_info.hbmColor, 0, height, pixel_buf, bmi_header, 0
        )
        ctypes.windll.user32.ReleaseDC(None, hdc)

        bmp_file_header = struct.pack(
            '<2sIHHI', b'BM', 54 + pixel_data_size, 0, 0, 54
        )
        icon_b64 = (
            "data:image/bmp;base64,"
            + base64.b64encode(bmp_file_header + bmi_header + pixel_buf.raw).decode('utf-8')
        )

        # Cleanup de handles GDI
        ctypes.windll.user32.DestroyIcon(shfi.hIcon)
        ctypes.windll.gdi32.DeleteObject(icon_info.hbmColor)
        ctypes.windll.gdi32.DeleteObject(icon_info.hbmMask)

        _icon_cache[clean_path] = icon_b64
        return icon_b64

    except Exception:
        return ""


def clear_icon_cache():
    """Limpa o cache de ícones (útil entre scans)."""
    _icon_cache.clear()
