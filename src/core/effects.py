import platform
import ctypes
from ctypes import wintypes
from .logger import get_logger

logger = get_logger("effects")

_WS_EX_LAYERED = 0x80000
_WS_EX_TRANSPARENT = 0x20
_GWL_EXSTYLE = -20

_DWM_BB_ENABLE = 0x00000001
_DWM_BB_BLURREGION = 0x00000002
_DWM_BB_TRANSITIONONMAXIMIZED = 0x00000004

_WCA_ACCENT_POLICY = 19

_ACCENT_DISABLED = 0
_ACCENT_ENABLE_GRADIENT = 1
_ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
_ACCENT_ENABLE_BLURBEHIND = 3
_ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
_ACCENT_ENABLE_HOSTBACKDROP = 5
_ACCENT_INVALID_STATE = 6


class _DWM_BLURBEHIND(ctypes.Structure):
    _fields_ = [
        ("dwFlags", ctypes.c_ulong),
        ("fEnable", ctypes.c_int),
        ("hRgnBlur", ctypes.c_void_p),
        ("fTransitionOnMaximized", ctypes.c_int),
    ]


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(_ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _try_load_dwm():
    try:
        return ctypes.WinDLL("dwmapi.dll")
    except Exception:
        return None


def _try_load_user32():
    try:
        return ctypes.WinDLL("user32.dll")
    except Exception:
        return None


def _set_window_composition(hwnd, accent_state, gradient_color=0):
    try:
        user32 = ctypes.windll.user32
        accent = _ACCENT_POLICY()
        accent.AccentState = accent_state
        accent.AccentFlags = 0
        accent.GradientColor = gradient_color
        data = _WINCOMPATTRDATA()
        data.Attribute = _WCA_ACCENT_POLICY
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.pointer(accent)
        result = user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        return result != 0
    except AttributeError:
        try:
            dwm = _try_load_dwm()
            if dwm is None:
                return False
            accent = _ACCENT_POLICY()
            accent.AccentState = accent_state
            accent.AccentFlags = 0
            accent.GradientColor = gradient_color
            data = _WINCOMPATTRDATA()
            data.Attribute = _WCA_ACCENT_POLICY
            data.SizeOfData = ctypes.sizeof(accent)
            data.Data = ctypes.pointer(accent)
            dwm.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
            return True
        except Exception:
            return False
    except Exception:
        return False


def apply_acrylic(hwnd, color_hex="#0a0a0a", opacity=0.35):
    if platform.system() != "Windows":
        return False
    try:
        if color_hex.startswith("#"):
            color_hex = color_hex[1:]
        b = int(color_hex[0:2], 16) if len(color_hex) >= 6 else 0
        g = int(color_hex[2:4], 16) if len(color_hex) >= 6 else 0
        r = int(color_hex[4:6], 16) if len(color_hex) >= 6 else 0
        a = max(0, min(255, int(opacity * 255)))
        gradient_color = (a << 24) | (r << 16) | (g << 8) | b
        return _set_window_composition(hwnd, _ACCENT_ENABLE_ACRYLICBLURBEHIND, gradient_color)
    except Exception as e:
        logger.debug("apply_acrylic failed: %s", e)
        return False


def apply_blur(hwnd):
    if platform.system() != "Windows":
        return False
    try:
        dwm = _try_load_dwm()
        if dwm is None:
            return False

        bb = _DWM_BLURBEHIND()
        bb.dwFlags = _DWM_BB_ENABLE
        bb.fEnable = True
        bb.hRgnBlur = None

        dwm.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
        return True
    except Exception as e:
        logger.debug("apply_blur failed: %s", e)
        return False


def remove_effects(hwnd):
    if platform.system() != "Windows":
        return False
    try:
        return _set_window_composition(hwnd, _ACCENT_DISABLED)
    except Exception:
        return False


def set_window_opacity(hwnd, opacity):
    if platform.system() != "Windows":
        return False
    try:
        user32 = _try_load_user32()
        if user32 is None:
            return False
        current = user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        new = current | _WS_EX_LAYERED
        user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, new)
        opacity = max(0, min(255, int(opacity * 255)))
        user32.SetLayeredWindowAttributes(hwnd, 0, opacity, 2)
        return True
    except Exception:
        return False
