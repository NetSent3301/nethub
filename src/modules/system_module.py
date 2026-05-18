import customtkinter as ctk
import platform
import psutil
import os
import subprocess
from tkinter import scrolledtext

from .base_module import BaseModule
from .shared import ToolFrameContainer


def _system_root():
    return os.environ.get("SystemDrive", "C:\\") if platform.system() == "Windows" else "/"


class SystemModule(BaseModule):
    name = "Kernel Telemetry"
    icon = "🧬"
    description = "Monitoreo y gestión del sistema"

    def build(self, parent):
        colors = self.colors
        self._build_tool_cards(parent, [
            ("Process Manager", "Gestiona procesos del sistema", self.process_manager, "⚙️"),
            ("Disk Analyzer", "Analiza particiones y almacenamiento", self.disk_analyzer, "💾"),
        ])

        info_frame = ctk.CTkFrame(parent, fg_color=colors["fg"], corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 20))

        info_text = (
            f"Sistema: {platform.system()} {platform.release()}\n"
            f"Procesador: {platform.processor() or 'N/A'}\n"
            f"Núcleos: {psutil.cpu_count()}\n"
            f"RAM Total: {psutil.virtual_memory().total / (1024**3):.1f} GB\n"
            f"Disco C: {psutil.disk_usage(_system_root()).percent}% usado"
        )
        ctk.CTkLabel(
            info_frame, text=info_text,
            font=("Arial", 12), text_color=colors["text"], justify="left"
        ).pack(pady=20, padx=20)

    def process_manager(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Process Manager", self.build, self.colors)
        win.pack(fill="both", expand=True)

        listbox = scrolledtext.ScrolledText(
            win, height=25,
            bg=self.colors["bg"], fg=self.colors["text"],
            insertbackground=self.colors["text"]
        )
        listbox.pack(pady=10, padx=20, fill="both", expand=True)

        def refresh():
            listbox.delete("1.0", "end")
            listbox.insert("end", f"{'PID':6} | {'NOMBRE':30} | {'CPU':8} | {'MEMORIA':8}\n")
            listbox.insert("end", f"{'-'*60}\n")
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    listbox.insert("end", f"{info['pid']:6} | {info['name']:30} | CPU: {info['cpu_percent']:5.1f}% | MEM: {info['memory_percent']:5.1f}%\n")
                except:
                    pass

        def kill_process():
            try:
                pid = int(pid_entry.get())
                psutil.Process(pid).terminate()
                refresh()
                app.toast.show(f"Proceso {pid} terminado", type="success")
            except:
                app.toast.show("Error al terminar proceso", type="error")

        refresh()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        pid_entry = ctk.CTkEntry(btn_frame, placeholder_text="PID", width=150)
        pid_entry.pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="Terminar", command=kill_process, fg_color="red", width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Refrescar", command=refresh, fg_color=self.colors["accent"], width=100).pack(side="left", padx=5)

    def disk_analyzer(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Disk Analyzer", self.build, self.colors)
        win.pack(fill="both", expand=True)

        output = ctk.CTkTextbox(win, height=350)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def analyze():
            output.delete("1.0", "end")
            output.insert("end", "Analizando almacenamiento...\n\n")
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    output.insert("end", f"  [+] Dispositivo: {part.device}\n")
                    output.insert("end", f"      Montaje: {part.mountpoint}\n")
                    output.insert("end", f"      FS: {part.fstype}\n")
                    output.insert("end", f"      Total: {usage.total / (1024**3):.1f} GB\n")
                    output.insert("end", f"      Usado: {usage.used / (1024**3):.1f} GB ({usage.percent}%)\n")
                    output.insert("end", f"      Libre: {usage.free / (1024**3):.1f} GB\n\n")
                except:
                    pass

        analyze()
