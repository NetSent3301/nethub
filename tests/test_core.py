import os
import sys
import json
import tempfile
import unittest
import warnings
import shutil

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

TEST_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)


def _setup_matplotlib_mocks():
    import types
    class MockFigure:
        def __init__(self, *a, **k): pass
        def add_subplot(self, *a, **k):
            ax = types.SimpleNamespace()
            ax.set_facecolor = lambda *a, **k: None
            ax.tick_params = lambda *a, **k: None
            ax.set_ylim = lambda *a, **k: None
            ax.set_xlim = lambda *a, **k: None
            ax.spines = {}
            ax.plot = lambda *a, **k: [types.SimpleNamespace(set_ydata=lambda *a, **k: None)]
            ax.fill_between = lambda *a, **k: None
            return ax
    class MockCanvas:
        def __init__(self, *a, **k): pass
        def get_tk_widget(self):
            return types.SimpleNamespace(pack=lambda *a, **k: None)
        def draw_idle(self): pass
    mock_matplotlib = types.ModuleType("matplotlib")
    mock_matplotlib.use = lambda *a, **k: None
    sys.modules["matplotlib"] = mock_matplotlib
    mock_figure = types.ModuleType("matplotlib.figure")
    mock_figure.Figure = MockFigure
    sys.modules["matplotlib.figure"] = mock_figure
    mock_backend = types.ModuleType("matplotlib.backends")
    sys.modules["matplotlib.backends"] = mock_backend
    mock_backend_tkagg = types.ModuleType("matplotlib.backends.backend_tkagg")
    mock_backend_tkagg.FigureCanvasTkAgg = MockCanvas
    sys.modules["matplotlib.backends.backend_tkagg"] = mock_backend_tkagg
    class MockCTk:
        class CTkFrame: pass
        class CTkLabel: pass
        class CTkButton: pass
        class CTkEntry: pass
        class CTkTextbox: pass
        class CTkScrollableFrame: pass
        class CTkTabview: pass
        class CTkProgressBar: pass
        class CTkCheckBox: pass
        class CTkSwitch: pass
        class CTkSegmentedButton: pass
        class CTkToplevel: pass
        class CTkCanvas: pass
        class CTkImage: pass
        class CTk: pass
        @staticmethod
        def set_appearance_mode(*a, **k): pass
        @staticmethod
        def set_default_color_theme(*a, **k): pass
    sys.modules["customtkinter"] = MockCTk()
    for mod in ["PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageTk", "PIL.ImageColor"]:
        sys.modules[mod] = types.ModuleType(mod)
    sys.modules["psutil"] = types.ModuleType("psutil")
    sys.modules["psutil"].cpu_count = lambda: 8
    sys.modules["psutil"].cpu_percent = lambda: 25.0
    sys.modules["psutil"].virtual_memory = lambda: types.SimpleNamespace(percent=50, total=8e9)
    sys.modules["psutil"].disk_partitions = lambda: []
    sys.modules["psutil"].disk_usage = lambda p: types.SimpleNamespace(total=500e9, used=250e9, free=250e9, percent=50)
    sys.modules["psutil"].net_connections = lambda *a, **k: []
    sys.modules["psutil"].net_io_counters = lambda: types.SimpleNamespace(bytes_sent=0, bytes_recv=0)
    sys.modules["psutil"].process_iter = lambda *a, **k: []


class _TempTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        for key in list(sys.modules.keys()):
            if key == "main" or key == "core" or key.startswith("modules"):
                del sys.modules[key]
        _setup_matplotlib_mocks()

    def tearDown(self):
        os.chdir(self._orig_cwd)
        try:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
        except:
            pass


class TestConfigManager(_TempTestBase):
    def test_load_default_config(self):
        from core import ConfigManager
        cm = ConfigManager()
        self.assertEqual(cm.config["theme"], "dark")
        self.assertTrue(cm.config["sound_effects"])
        self.assertIn("appearance_mode", cm.config)

    def test_save_and_load_config(self):
        from core import ConfigManager
        cm = ConfigManager()
        cm.config["theme"] = "matrix"
        cm.config["sound_effects"] = False
        cm.save_config()
        cm2 = ConfigManager()
        self.assertEqual(cm2.config["theme"], "matrix")
        self.assertFalse(cm2.config["sound_effects"])

    def test_get_colors_returns_dict(self):
        from core import ConfigManager
        cm = ConfigManager()
        colors = cm.get_colors()
        self.assertIsInstance(colors, dict)
        self.assertIn("bg", colors)
        self.assertIn("accent", colors)
        self.assertIn("text", colors)

    def test_get_colors_dark_theme(self):
        from core import ConfigManager
        cm = ConfigManager()
        cm.config["theme"] = "dark"
        colors = cm.get_colors()
        self.assertEqual(colors["bg"], "#0a0a0a")
        self.assertEqual(colors["accent"], "#2a6a8a")

    def test_custom_theme(self):
        from core import ConfigManager
        cm = ConfigManager()
        cm.config["theme"] = "custom"
        cm.config["custom_colors"] = {
            "bg": "#ffffff", "fg": "#f0f0f0", "accent": "#ff0000",
            "text": "#000000", "text_secondary": "#666666",
            "hover": "#e0e0e0", "sidebar": "#f5f5f5",
            "active": "#ff0000", "border": "#cccccc",
        }
        colors = cm.get_colors()
        self.assertIn("bg", colors)


class TestUserManagerBcrypt(_TempTestBase):
    def test_register_and_login(self):
        from core import UserManager
        um = UserManager()
        success, msg = um.register("testuser", "password123", "", email="test@test.com")
        self.assertTrue(success)
        self.assertEqual(msg, "Registro exitoso")
        success, result = um.login("testuser", "password123")
        self.assertTrue(success)

    def test_login_wrong_password(self):
        from core import UserManager
        um = UserManager()
        um.register("testuser", "password123", "")
        success, result = um.login("testuser", "wrongpassword")
        self.assertFalse(success)
        self.assertIn("intentos restantes", result)

    def test_login_nonexistent_user(self):
        from core import UserManager
        um = UserManager()
        success, result = um.login("nonexistent", "anything")
        self.assertFalse(success)

    def test_password_hashed_with_bcrypt(self):
        from core import UserManager
        um = UserManager()
        um.register("testuser", "password123", "")
        stored_hash = um.users["testuser"]["password"]
        self.assertTrue(stored_hash.startswith("$2"),
                        f"Password should be bcrypt hash, got: {stored_hash[:10]}...")

    def test_change_password(self):
        from core import UserManager
        um = UserManager()
        um.register("testuser", "oldpass", "")
        success, msg = um.change_password("testuser", "newpass")
        self.assertTrue(success)
        success, result = um.login("testuser", "newpass")
        self.assertTrue(success)
        success, result = um.login("testuser", "oldpass")
        self.assertFalse(success)

    def test_duplicate_registration(self):
        from core import UserManager
        um = UserManager()
        um.register("testuser", "password123", "")
        success, msg = um.register("testuser", "anotherpass", "")
        self.assertFalse(success)
        self.assertEqual(msg, "Usuario ya existe")

    def test_account_lockout(self):
        from core import UserManager
        um = UserManager()
        um.register("testuser", "password123", "")
        for _ in range(5):
            um.login("testuser", "wrong")
        success, result = um.login("testuser", "password123")
        self.assertFalse(success)
        self.assertIn("bloqueada", result)

    def test_legacy_sha256_migration(self):
        from core import UserManager
        import hashlib
        um = UserManager()
        um.users["legacy_user"] = {
            "password": hashlib.sha256(b"mypass").hexdigest(),
            "avatar": "", "display_name": "legacy_user", "email": "",
            "created": 0, "last_login": None, "failed_attempts": 0,
        }
        um.save_users()
        success, result = um.login("legacy_user", "mypass")
        self.assertTrue(success)
        stored = um.users["legacy_user"]["password"]
        self.assertTrue(stored.startswith("$2"),
                        f"Legacy password should be migrated to bcrypt, got: {stored[:10]}...")


class TestModuleManager(unittest.TestCase):
    def setUp(self):
        for key in list(sys.modules.keys()):
            if key == "main" or key == "core" or key.startswith("modules"):
                del sys.modules[key]
        os.chdir(PROJECT_DIR)
        _setup_matplotlib_mocks()
        from modules.module_manager import ModuleManager
        self.ModuleManager = ModuleManager

    def test_module_manager_loads_builtin(self):
        class FakeApp:
            colors = {
                "bg": "#0a0a0a", "fg": "#1a1a1a", "accent": "#2a6a8a",
                "accent_light": "#3a8aaa", "text": "#e0e0e0",
                "text_secondary": "#a0a0a0", "hover": "#2a4a5a",
                "sidebar": "#0a0a0a", "active": "#2a6a8a",
                "border": "#2a2a2a", "success": "#2a6a3a",
                "error": "#8a2a2a", "warning": "#8a6a2a",
            }
        mm = self.ModuleManager(FakeApp())
        mm.discover_builtin()
        self.assertGreaterEqual(len(mm.modules), 11)

    def test_module_has_required_attributes(self):
        class FakeApp:
            colors = {
                "bg": "#0a0a0a", "fg": "#1a1a1a", "accent": "#2a6a8a",
                "accent_light": "#3a8aaa", "text": "#e0e0e0",
                "text_secondary": "#a0a0a0", "hover": "#2a4a5a",
                "sidebar": "#0a0a0a", "active": "#2a6a8a",
                "border": "#2a2a2a", "success": "#2a6a3a",
                "error": "#8a2a2a", "warning": "#8a6a2a",
            }
        mm = self.ModuleManager(FakeApp())
        mm.discover_builtin()
        for name, mod in mm.modules.items():
            self.assertTrue(hasattr(mod, "name"))
            self.assertTrue(hasattr(mod, "icon"))
            self.assertTrue(hasattr(mod, "description"))
            self.assertTrue(callable(getattr(mod, "build", None)))

    def test_module_info(self):
        class FakeApp:
            colors = {
                "bg": "#0a0a0a", "fg": "#1a1a1a", "accent": "#2a6a8a",
                "accent_light": "#3a8aaa", "text": "#e0e0e0",
                "text_secondary": "#a0a0a0", "hover": "#2a4a5a",
                "sidebar": "#0a0a0a", "active": "#2a6a8a",
                "border": "#2a2a2a", "success": "#2a6a3a",
                "error": "#8a2a2a", "warning": "#8a6a2a",
            }
        mm = self.ModuleManager(FakeApp())
        mm.load_all()
        info = mm.get_info()
        self.assertIsInstance(info, list)
        self.assertGreater(len(info), 0)
        for item in info:
            self.assertIn("name", item)
            self.assertIn("icon", item)
            self.assertIn("description", item)
            self.assertIn("custom", item)
            self.assertIn("class", item)


class TestImprovedGLI(_TempTestBase):
    def setUp(self):
        super().setUp()
        from core import ImprovedGLI
        self.ImprovedGLI = ImprovedGLI

    def test_execute_safe_code(self):
        gli = self.ImprovedGLI(host="http://localhost:99999")
        result = gli.execute_code("print(2 + 2)")
        self.assertIn("4", result)

    def test_execute_code_returns_output(self):
        gli = self.ImprovedGLI(host="http://localhost:99999")
        result = gli.execute_code('print("hola mundo")')
        self.assertIn("hola mundo", result)

    def test_execute_code_handles_error(self):
        gli = self.ImprovedGLI(host="http://localhost:99999")
        result = gli.execute_code("raise ValueError('test error')")
        self.assertIn("Error", result)

    def test_execute_code_no_output(self):
        gli = self.ImprovedGLI(host="http://localhost:99999")
        result = gli.execute_code("x = 42")
        self.assertIn("ejecutado", result)


class TestColorContrast(_TempTestBase):
    def test_all_themes_load(self):
        from core import ConfigManager
        cm = ConfigManager()
        for theme in ["dark", "blood", "matrix", "cyber"]:
            cm.config["theme"] = theme
            colors = cm.get_colors()
            self.assertIn("bg", colors)
            self.assertIn("fg", colors)
            self.assertIn("accent", colors)
            self.assertIn("text", colors)


if __name__ == "__main__":
    unittest.main()
