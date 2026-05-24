import shutil
import socket
import platform
import psutil
import threading
import time
import datetime
import json
import os
from collections import defaultdict, OrderedDict


class UserProfile:
    """User behavior profile — tracks usage for smart adaptation."""

    def __init__(self):
        self.module_uses = defaultdict(int)
        self.feature_uses = defaultdict(int)
        self.last_used = {}
        self.session_count = 0
        self.total_time_ms = 0
        self.favorite_modules = []
        self.search_history = []
        self.theme_preference = None
        self.preferred_scan_profile = "normal"
        self.peak_hours = defaultdict(int)

    def record_module_use(self, module_name):
        self.module_uses[module_name] += 1
        self.last_used[module_name] = time.time()

    def record_feature_use(self, feature_name):
        self.feature_uses[feature_name] += 1

    def record_search(self, query):
        self.search_history.insert(0, query)
        if len(self.search_history) > 50:
            self.search_history.pop()

    def get_top_modules(self, n=5):
        return sorted(self.module_uses, key=self.module_uses.get, reverse=True)[:n]

    def get_top_features(self, n=5):
        return sorted(self.feature_uses, key=self.feature_uses.get, reverse=True)[:n]

    def is_favorite(self, module_name, threshold=5):
        return self.module_uses.get(module_name, 0) >= threshold

    def to_dict(self):
        return {
            "module_uses": dict(self.module_uses),
            "feature_uses": dict(self.feature_uses),
            "last_used": {k: v for k, v in self.last_used.items()},
            "session_count": self.session_count,
            "total_time_ms": self.total_time_ms,
            "favorite_modules": self.favorite_modules,
            "theme_preference": self.theme_preference,
            "preferred_scan_profile": self.preferred_scan_profile,
        }

    @classmethod
    def from_dict(cls, data):
        p = cls()
        p.module_uses.update(data.get("module_uses", {}))
        p.feature_uses.update(data.get("feature_uses", {}))
        p.last_used.update(data.get("last_used", {}))
        p.session_count = data.get("session_count", 0)
        p.total_time_ms = data.get("total_time_ms", 0)
        p.favorite_modules = data.get("favorite_modules", [])
        p.theme_preference = data.get("theme_preference")
        p.preferred_scan_profile = data.get("preferred_scan_profile", "normal")
        return p


class AdaptationEngine:
    """Full environmental + user adaptation system.

    Tiers (configurable in settings):
        - low:      < 4GB RAM, 2 cores, slow/no network
        - medium:   4-8GB RAM, 4 cores
        - high:     8-16GB RAM, 8+ cores
        - ultra:    16+ GB RAM, 16+ cores
        - auto:     determined dynamically
    """

    TIER_CONFIGS = {
        "low": {
            "animations": False, "blur": False, "glass": False,
            "max_threads": 25, "scan_timeout": 2.0, "poll_interval": 2.0,
            "max_concurrent_processes": 2, "radar_enabled": False,
            "wallpaper_opacity": 0.1, "slide_animation": False,
        },
        "medium": {
            "animations": True, "blur": True, "glass": True,
            "max_threads": 100, "scan_timeout": 1.5, "poll_interval": 1.0,
            "max_concurrent_processes": 4, "radar_enabled": True,
            "wallpaper_opacity": 0.2, "slide_animation": True,
        },
        "high": {
            "animations": True, "blur": True, "glass": True,
            "max_threads": 300, "scan_timeout": 1.0, "poll_interval": 0.5,
            "max_concurrent_processes": 8, "radar_enabled": True,
            "wallpaper_opacity": 0.3, "slide_animation": True,
        },
        "ultra": {
            "animations": True, "blur": True, "glass": True,
            "max_threads": 500, "scan_timeout": 0.5, "poll_interval": 0.25,
            "max_concurrent_processes": 16, "radar_enabled": True,
            "wallpaper_opacity": 0.4, "slide_animation": True,
        },
    }

    def __init__(self, config_manager=None, data_dir=None):
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_ttl = {}
        self._config = config_manager
        self._data_dir = data_dir or os.path.dirname(
            os.path.abspath(__file__) + "/../../")

        # User profile
        self.user = UserProfile()
        self._profile_path = os.path.join(self._data_dir, "user_profile.json")
        self._load_profile()

        # Current tier (detected or manual)
        self._tier = "auto"
        self._manual_tier = None
        self._last_tier_check = 0

        # Callbacks for config changes
        self._listeners = []

    # ── Profile persistence ──────────────────────────────────────────

    def _profile_path_resolved(self):
        return os.path.join(self._data_dir, "user_profile.json")

    def _load_profile(self):
        try:
            path = self._profile_path
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                self.user = UserProfile.from_dict(data)
        except Exception:
            self.user = UserProfile()

    def save_profile(self):
        try:
            path = self._profile_path
            with open(path, "w") as f:
                json.dump(self.user.to_dict(), f, indent=2)
        except Exception:
            pass

    # ── System resource detection ────────────────────────────────────

    def _cached(self, key, ttl=60):
        with self._lock:
            if key in self._cache and time.time() - self._cache_ttl.get(key, 0) < ttl:
                return self._cache[key]
        return None

    def _set_cached(self, key, value, ttl=60):
        with self._lock:
            self._cache[key] = value
            self._cache_ttl[key] = time.time()

    def detect_system_tools(self, force=False):
        key = "sys_tools"
        c = self._cached(key, 120)
        if c and not force:
            return c
        tools = {
            "nmap": self._which("nmap"), "ping": self._which("ping"),
            "curl": self._which("curl"), "wget": self._which("wget"),
            "traceroute": self._which("traceroute") or self._which("tracert"),
            "netstat": self._which("netstat"), "whois": self._which("whois"),
            "dig": self._which("dig"), "nslookup": self._which("nslookup"),
        }
        self._set_cached(key, tools, 120)
        return tools

    def _which(self, name):
        return shutil.which(name) is not None

    def check_network(self, force=False):
        key = "network"
        c = self._cached(key, 30)
        if c and not force:
            return c
        r = {"internet": False, "latency_ms": None, "local_ip": None, "error": None}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            t0 = time.time()
            s.connect(("8.8.8.8", 53))
            s.close()
            r["latency_ms"] = int((time.time() - t0) * 1000)
            r["internet"] = True
        except Exception as e:
            r["error"] = str(e)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            r["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            r["local_ip"] = "127.0.0.1"
        self._set_cached(key, r, 30)
        return r

    def detect_python_capabilities(self, force=False):
        key = "pycaps"
        c = self._cached(key, 300)
        if c and not force:
            return c
        caps = {"scapy": False, "cryptography": False, "bs4": False, "paramiko": False}
        for pkg in caps:
            try:
                __import__(pkg)
                caps[pkg] = True
            except ImportError:
                pass
        self._set_cached(key, caps, 300)
        return caps

    def get_performance_tier(self):
        """Auto-detect: low|medium|high|ultra based on system resources."""
        if self._manual_tier and self._manual_tier != "auto":
            return self._manual_tier
        ram = psutil.virtual_memory().total / (1024**3)
        cores = psutil.cpu_count(logical=True) or 2
        if ram < 3 or cores <= 2:
            return "low"
        elif ram < 7 or cores <= 4:
            return "medium"
        elif ram < 15 or cores <= 8:
            return "high"
        else:
            return "ultra"

    def set_tier(self, tier):
        self._manual_tier = tier
        self.save_profile()

    def get_tier_config(self):
        tier = self.get_performance_tier()
        return dict(self.TIER_CONFIGS.get(tier, self.TIER_CONFIGS["medium"]))

    # ── User behavior tracking ───────────────────────────────────────

    def record_module_use(self, module_name):
        self.user.record_module_use(module_name)
        self.save_profile()

    def record_feature_use(self, feature_name):
        self.user.record_feature_use(feature_name)

    def record_search(self, query):
        self.user.record_search(query)

    def record_session_start(self):
        self.user.session_count += 1
        self._session_start = time.time()

    def record_session_end(self):
        if hasattr(self, "_session_start"):
            self.user.total_time_ms += int((time.time() - self._session_start) * 1000)
            self.save_profile()

    def get_frequent_modules(self, n=5):
        return self.user.get_top_modules(n)

    def get_frequent_features(self, n=5):
        return self.user.get_top_features(n)

    def get_smart_suggestions(self, n=3):
        """Generate contextual suggestions based on usage + environment."""
        suggestions = []
        top = self.get_frequent_modules(3)
        # Suggest continuing with favorite modules
        for m in top:
            suggestions.append({
                "type": "module",
                "label": f"Continuar con {m}",
                "value": m,
                "score": self.user.module_uses.get(m, 0),
            })
        # Suggest based on network
        net = self.check_network()
        if not net.get("internet"):
            suggestions.append({
                "type": "info",
                "label": "Sin internet — algunos módulos no disponibles",
                "value": None, "score": 0,
            })
        # Suggest based on detected tools
        tools = self.detect_system_tools()
        if tools.get("nmap") and "nmap_gui" not in self.user.feature_uses:
            suggestions.append({
                "type": "feature",
                "label": "Nmap detectado — probar escaneo avanzado",
                "value": "nmap_gui", "score": 5,
            })
        # Suggest performance improvements
        tier = self.get_performance_tier()
        if tier == "low":
            suggestions.append({
                "type": "setting",
                "label": "Rendimiento bajo detectado — desactivar animaciones",
                "value": "low_perf", "score": 3,
            })
        return sorted(suggestions, key=lambda x: x["score"], reverse=True)[:n]

    # ── Network-adaptive scan profiles ───────────────────────────────

    def get_scan_profile(self, profile="auto"):
        profiles = {
            "quick":  {"timeout": 1.0, "threads": 50,  "ports": "21,22,23,25,53,80,110,143,443,445,993,995,1433,1521,3306,3389,5432,5900,8080,8443,27017"},
            "normal": {"timeout": 1.5, "threads": 100, "ports": "1-10000"},
            "deep":   {"timeout": 3.0, "threads": 200, "ports": "1-65535"},
        }
        if profile != "auto":
            return profiles.get(profile, profiles["normal"])

        tier = self.get_performance_tier()
        base = self.TIER_CONFIGS[tier]
        net = self.check_network()
        if net.get("internet") and net.get("latency_ms", 999) < 80:
            threads = base["max_threads"]
            timeout = max(0.3, base["scan_timeout"] * 0.7)
        elif net.get("internet"):
            threads = int(base["max_threads"] * 0.6)
            timeout = base["scan_timeout"]
        else:
            threads = int(base["max_threads"] * 0.3)
            timeout = base["scan_timeout"] * 1.5

        user_pref = self.user.preferred_scan_profile
        if user_pref == "quick":
            ports = profiles["quick"]["ports"]
        elif user_pref == "deep":
            ports = profiles["deep"]["ports"]
        else:
            ports = profiles["normal"]["ports"]

        return {"timeout": round(timeout, 1), "threads": max(5, threads), "ports": ports}

    def get_default_scan_targets(self):
        targets = ["127.0.0.1"]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            parts = ip.split(".")
            targets.insert(0, ip)
            targets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.1")
            targets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.254")
        except Exception:
            pass
        return targets

    def get_available_features(self):
        tools = self.detect_system_tools()
        caps = self.detect_python_capabilities()
        available = []
        if tools.get("nmap"):         available.append("nmap_integration")
        if caps.get("scapy"):         available.append("packet_capture")
        if caps.get("cryptography"):  available.append("advanced_crypto")
        if caps.get("bs4"):           available.append("html_parsing")
        if caps.get("paramiko"):      available.append("ssh_client")
        return available

    def get_config_recommendations(self):
        recs = []
        tools = self.detect_system_tools()
        net = self.check_network()
        tier = self.get_performance_tier()

        if not net.get("internet"):
            recs.append({"setting": "offline_mode", "value": True,
                         "reason": "Sin internet"})
        if tier == "low":
            recs.append({"setting": "performance_tier", "value": "low",
                         "reason": "Recursos limitados"})
        if not tools.get("nmap"):
            recs.append({"setting": "use_internal_scanner", "value": True,
                         "reason": "nmap no instalado"})
        if tier in ("high", "ultra") and net.get("internet"):
            recs.append({"setting": "radar_enabled", "value": True,
                         "reason": "Sistema apto para monitoreo continuo"})
        return recs

    def full_report(self):
        return {
            "system": {
                "platform": platform.system(),
                "release": platform.release(),
                "cpu_cores": psutil.cpu_count(logical=True),
                "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
            },
            "performance_tier": self.get_performance_tier(),
            "tier_config": self.get_tier_config(),
            "network": self.check_network(),
            "tools": self.detect_system_tools(),
            "python_capabilities": self.detect_python_capabilities(),
            "available_features": self.get_available_features(),
            "user": {
                "sessions": self.user.session_count,
                "total_time_hours": round(self.user.total_time_ms / 3600000, 1),
                "top_modules": self.get_frequent_modules(5),
                "top_features": self.get_frequent_features(5),
            },
            "recommendations": self.get_config_recommendations(),
            "suggestions": self.get_smart_suggestions(3),
        }

    # ── Config suggestions for Settings UI ────────────────────────────

    def tier_choices(self):
        return [("auto", "Automático"), ("low", "Bajo"), ("medium", "Medio"),
                ("high", "Alto"), ("ultra", "Ultra")]

    def current_tier_label(self):
        t = self.get_performance_tier()
        labels = {"low": "Bajo", "medium": "Medio", "high": "Alto", "ultra": "Ultra"}
        return labels.get(t, t)
