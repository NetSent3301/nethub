from PIL import Image, ImageDraw, ImageFilter
import os
import json
import math
from collections import Counter
from .logger import get_logger

logger = get_logger("wallpaper")

DEFAULT_WALLPAPER_CONFIG = {
    "path": None,
    "mode": "cover",
    "opacity": 0.25,
    "blur_radius": 20,
    "effect": "acrylic",
    "auto_theme": False,
    "glass_enabled": True,
    "glass_opacity": 0.2,
    "glass_blur": 10,
    "ui_opacity": 1.0,
}


class WallpaperManager:
    def __init__(self, config=None):
        self.config = config or {}
        self._wallpaper_image = None
        self._wallpaper_pil = None
        self._colors = None

    @staticmethod
    def get_defaults():
        return dict(DEFAULT_WALLPAPER_CONFIG)

    def load_wallpaper(self, path=None):
        path = path or self.config.get("path")
        if not path or not os.path.exists(path):
            self._wallpaper_pil = None
            self._wallpaper_image = None
            return False
        try:
            img = Image.open(path).convert("RGBA")
            self._wallpaper_pil = img
            self._colors = None
            return True
        except Exception as e:
            logger.warning("Error loading wallpaper: %s", e)
            self._wallpaper_pil = None
            return False

    def get_wallpaper_pil(self):
        return self._wallpaper_pil

    def get_wallpaper_ctk(self, width, height):
        if self._wallpaper_pil is None or width < 10 or height < 10:
            return None
        try:
            mode = self.config.get("mode", "cover")
            img = self._wallpaper_pil.copy()
            img_w, img_h = img.size
            if mode == "cover":
                ratio = max(width / img_w, height / img_h)
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - width) // 2
                top = (new_h - height) // 2
                img = img.crop((left, top, left + width, top + height))
            elif mode == "contain":
                ratio = min(width / img_w, height / img_h)
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                left = (width - new_w) // 2
                top = (height - new_h) // 2
                bg.paste(img, (left, top))
                img = bg
            elif mode == "stretch":
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            else:
                img = img.resize((width, height), Image.Resampling.LANCZOS)

            blur = self.config.get("blur_radius", 0)
            if blur > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=blur))

            opacity = max(0.0, min(1.0, self.config.get("opacity", 0.3)))
            if opacity < 1.0:
                r, g, b, a = img.split()
                a = a.point(lambda x: int(x * opacity))
                img = Image.merge("RGBA", (r, g, b, a))

            import customtkinter as ctk
            return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
        except Exception as e:
            logger.warning("Error rendering wallpaper: %s", e)
            return None

    def get_wallpaper_photo(self, width, height):
        from PIL import ImageTk
        ctk_img = self.get_wallpaper_ctk(width, height)
        if ctk_img is None:
            return None
        try:
            pil_img = ctk_img._light_image
            if pil_img:
                return ImageTk.PhotoImage(pil_img.resize((width, height), Image.Resampling.LANCZOS))
        except Exception:
            pass
        return None

    def extract_colors(self, num_colors=6):
        if self._wallpaper_pil is None:
            return None
        if self._colors is not None:
            return self._colors

        try:
            img = self._wallpaper_pil.copy().convert("RGB")
            small = img.resize((64, 64), Image.Resampling.LANCZOS)
            pixels = list(small.getdata())
            total = len(pixels)

            color_counts = Counter(pixels)
            dominant = color_counts.most_common(num_colors * 2)

            def color_score(item):
                r, g, b = item[0]
                count = item[1]
                gray_penalty = 0
                if abs(r - g) < 15 and abs(g - b) < 15 and abs(r - b) < 15:
                    gray_penalty = -count * 0.5
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                extreme = 0
                if lum < 20 or lum > 235:
                    extreme = -count * 0.7
                return count + gray_penalty + extreme

            ranked = sorted(dominant, key=color_score, reverse=True)
            ranked = [c for c in ranked if color_score(c) > 0][:num_colors]

            if not ranked:
                ranked = dominant[:num_colors]

            def luminance(r, g, b):
                return 0.2126 * r + 0.7152 * g + 0.0722 * b

            def is_dark(r, g, b):
                return luminance(r, g, b) < 128

            dark_colors = [c for c in ranked if is_dark(*c[0])]
            light_colors = [c for c in ranked if not is_dark(*c[0])]

            colors = {}
            if dark_colors:
                r, g, b = dark_colors[0][0]
                colors["bg"] = f"#{r:02x}{g:02x}{b:02x}"
            else:
                colors["bg"] = "#0a0a0a"

            if len(ranked) > 1:
                r, g, b = ranked[1][0]
                colors["fg"] = f"#{r:02x}{g:02x}{b:02x}"
            else:
                r, g, b = ranked[0][0]
                fg_r = max(0, r - 30)
                fg_g = max(0, g - 30)
                fg_b = max(0, b - 30)
                colors["fg"] = f"#{fg_r:02x}{fg_g:02x}{fg_b:02x}"

            accent_candidates = [c for c in ranked if is_dark(*c[0]) and c != ranked[0]]
            if not accent_candidates and len(ranked) > 0:
                accent_candidates = [ranked[0]]

            if accent_candidates:
                r, g, b = accent_candidates[0][0]
                if luminance(r, g, b) > 128:
                    r, g, b = max(0, r - 80), max(0, g - 80), max(0, b - 80)
                colors["accent"] = f"#{r:02x}{g:02x}{b:02x}"
                ac_r = min(255, r + 40)
                ac_g = min(255, g + 40)
                ac_b = min(255, b + 40)
                colors["accent_light"] = f"#{ac_r:02x}{ac_g:02x}{ac_b:02x}"
            else:
                colors["accent"] = "#2a6a8a"
                colors["accent_light"] = "#3a8aaa"

            if light_colors:
                r, g, b = light_colors[0][0]
                colors["text"] = f"#{r:02x}{g:02x}{b:02x}"
            else:
                colors["text"] = "#e0e0e0"

            if len(light_colors) > 1:
                r, g, b = light_colors[1][0]
                colors["text_secondary"] = f"#{r:02x}{g:02x}{b:02x}"
            else:
                colors["text_secondary"] = "#a0a0a0"

            if dark_colors:
                r, g, b = dark_colors[-1][0]
                hover_r = min(255, r + 40)
                hover_g = min(255, g + 40)
                hover_b = min(255, b + 40)
                colors["hover"] = f"#{hover_r:02x}{hover_g:02x}{hover_b:02x}"
            else:
                colors["hover"] = "#2a4a5a"

            colors["sidebar"] = colors.get("bg", "#0a0a0a")
            colors["active"] = colors.get("accent", "#2a6a8a")

            if dark_colors:
                r, g, b = dark_colors[0][0]
                border_r = min(255, r + 50)
                border_g = min(255, g + 50)
                border_b = min(255, b + 50)
                colors["border"] = f"#{border_r:02x}{border_g:02x}{border_b:02x}"
            else:
                colors["border"] = "#2a2a2a"

            colors["success"] = "#2a6a3a"
            colors["error"] = "#8a2a2a"
            colors["warning"] = "#8a6a2a"

            self._colors = colors
            return colors
        except Exception as e:
            logger.warning("Error extracting colors: %s", e)
            return None

    def clear_cache(self):
        self._wallpaper_image = None
        self._colors = None
