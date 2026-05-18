import customtkinter as ctk
import os
import threading
import hashlib
from tkinter import filedialog

from .base_module import BaseModule
from .shared import ToolFrameContainer


class FilesModule(BaseModule):
    name = "Secure Vault"
    icon = "📁"
    description = "Gestión y análisis de archivos"

    def build(self, parent):
        self._build_tool_cards(parent, [
            ("File Search", "Búsqueda avanzada de archivos", self.file_search, "🔎"),
            ("Duplicate Finder", "Encuentra archivos duplicados", self.dup_finder, "📑"),
            ("Hash Calculator", "Calcula firmas MD5/SHA", self.file_hash, "🔐"),
            ("Batch Renamer", "Renombrado masivo por patrón", self.batch_rename, "✏️"),
        ])

    def file_search(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "File Search", self.build, self.colors)
        win.pack(fill="both", expand=True)

        search_entry = ctk.CTkEntry(win, placeholder_text="Nombre del archivo", width=300)
        search_entry.pack(pady=10)
        path_entry = ctk.CTkEntry(win, placeholder_text="Directorio raíz", width=300)
        path_entry.pack(pady=10)

        def pick_folder():
            folder = filedialog.askdirectory()
            if folder:
                path_entry.delete(0, "end")
                path_entry.insert(0, folder)

        ctk.CTkButton(win, text="📁 Seleccionar Directorio", command=pick_folder, fg_color=self.colors["hover"]).pack(pady=5)

        output = ctk.CTkTextbox(win, height=350)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def search():
            name = search_entry.get().lower()
            path = path_entry.get()
            if not name or not path:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Buscando '{name}' en '{path}'...\n\n")

            def run():
                count = 0
                for root, dirs, files in os.walk(path):
                    if not win.winfo_exists():
                        return
                    for file in files:
                        if name in file.lower():
                            count += 1
                            app.after(0, lambda f=os.path.join(root, file): output.insert("end", f"  [+] {f}\n"))
                    if count > 200:
                        app.after(0, lambda: output.insert("end", "\n[!] Demasiados resultados (>200). Búsqueda truncada.\n"))
                        break
                app.after(0, lambda: output.insert("end", f"\n[!] Completado. {count} archivos encontrados."))
                app.after(0, lambda: app.toast.show(f"{count} archivos", type="success"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="Buscar", command=search, fg_color=self.colors["accent"]).pack(pady=10)

    def dup_finder(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Duplicate Finder", self.build, self.colors)
        win.pack(fill="both", expand=True)

        path_entry = ctk.CTkEntry(win, placeholder_text="Directorio a escanear", width=400)
        path_entry.pack(pady=10)

        def pick_folder():
            folder = filedialog.askdirectory()
            if folder:
                path_entry.delete(0, "end")
                path_entry.insert(0, folder)

        ctk.CTkButton(win, text="📁 Seleccionar Directorio", command=pick_folder, fg_color=self.colors["hover"]).pack(pady=5)

        output = ctk.CTkTextbox(win, height=400)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def find():
            path = path_entry.get()
            if not path:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Escaneando duplicados en '{path}'...\n\n")
            hashes = {}

            def run():
                dups_found = 0
                for root, dirs, files in os.walk(path):
                    if not win.winfo_exists():
                        return
                    for file in files:
                        full = os.path.join(root, file)
                        try:
                            with open(full, 'rb') as f:
                                file_hash = hashlib.md5(f.read(1024*1024)).hexdigest()
                            if file_hash in hashes:
                                dups_found += 1
                                app.after(0, lambda f1=full, f2=hashes[file_hash]: output.insert("end", f"⚠️ DUPLICADO:\n   └─ {f2}\n   └─ {f1}\n\n"))
                            else:
                                hashes[file_hash] = full
                        except:
                            pass
                app.after(0, lambda: output.insert("end", f"Escaneo completo. {dups_found} duplicados."))
                app.after(0, lambda: app.toast.show(f"{dups_found} duplicados", type="info"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="Buscar Duplicados", command=find, fg_color=self.colors["accent"]).pack(pady=10)

    def file_hash(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Hash Calculator", self.build, self.colors)
        win.pack(fill="both", expand=True)

        def select():
            file = filedialog.askopenfilename()
            if file:
                file_entry.delete(0, "end")
                file_entry.insert(0, file)

        file_entry = ctk.CTkEntry(win, placeholder_text="Selecciona un archivo...", width=400)
        file_entry.pack(pady=10)
        ctk.CTkButton(win, text="🔍 Buscar Archivo", command=select, fg_color=self.colors["hover"]).pack(pady=5)

        output = ctk.CTkTextbox(win, height=250)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def calculate():
            file = file_entry.get()
            if not os.path.exists(file) or os.path.isdir(file):
                app.toast.show("Archivo no válido", type="error")
                return
            output.delete("1.0", "end")
            output.insert("end", "Calculando firmas...\n\n")
            try:
                with open(file, 'rb') as f:
                    data = f.read()
                output.insert("end", f"📁 {os.path.basename(file)}\n")
                output.insert("end", f"📏 {len(data) / 1024:.2f} KB\n\n")
                output.insert("end", f"🔐 MD5:    {hashlib.md5(data).hexdigest()}\n")
                output.insert("end", f"🔐 SHA1:   {hashlib.sha1(data).hexdigest()}\n")
                output.insert("end", f"🔐 SHA256: {hashlib.sha256(data).hexdigest()}\n")
                app.toast.show("Hashes calculados", type="success")
            except:
                output.insert("end", "❌ Error al leer el archivo.")
                app.toast.show("Error", type="error")

        ctk.CTkButton(win, text="Calcular", command=calculate, fg_color=self.colors["accent"]).pack(pady=10)

    def batch_rename(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Batch Renamer", self.build, self.colors)
        win.pack(fill="both", expand=True)

        path_entry = ctk.CTkEntry(win, placeholder_text="Directorio", width=400)
        path_entry.pack(pady=10)

        def pick_folder():
            folder = filedialog.askdirectory()
            if folder:
                path_entry.delete(0, "end")
                path_entry.insert(0, folder)

        ctk.CTkButton(win, text="📁 Seleccionar Directorio", command=pick_folder, fg_color=self.colors["hover"]).pack(pady=5)

        pattern_entry = ctk.CTkEntry(win, placeholder_text="Patrón (ej: archivo_{n})", width=400)
        pattern_entry.pack(pady=10)
        output = ctk.CTkTextbox(win, height=300)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def rename():
            path = path_entry.get()
            pattern = pattern_entry.get()
            if not path or not pattern:
                return
            if not os.path.exists(path):
                app.toast.show("Directorio inválido", type="error")
                return
            output.delete("1.0", "end")
            output.insert("end", "Renombrando...\n\n")
            try:
                files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                count = 0
                for i, file in enumerate(files):
                    ext = os.path.splitext(file)[1]
                    new_name = pattern.replace("{n}", f"{i+1:02d}") + ext
                    try:
                        os.rename(os.path.join(path, file), os.path.join(path, new_name))
                        output.insert("end", f"  [+] {file}  →  {new_name}\n")
                        count += 1
                    except:
                        output.insert("end", f"  [-] Error: {file}\n")
                output.insert("end", f"\n[!] Renombrados {count} archivos.")
                app.toast.show(f"{count} archivos renombrados", type="success")
            except Exception as e:
                output.insert("end", f"❌ Error: {str(e)}")

        ctk.CTkButton(win, text="Renombrar", command=rename, fg_color=self.colors["accent"]).pack(pady=10)
