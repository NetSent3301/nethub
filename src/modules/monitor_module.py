import customtkinter as ctk
import psutil
import os
import platform

from .base_module import BaseModule
from .shared import AnimatedGraph


def _system_root():
    return os.environ.get("SystemDrive", "C:\\") if platform.system() == "Windows" else "/"


class MonitorModule(BaseModule):
    name = "Live Sentinel"
    icon = "📊"
    description = "Monitor en tiempo real del sistema"

    def build(self, parent):
        colors = self.colors
        app = self.app

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(frame, text="📊 REAL-TIME THREAT SENTINEL MAP", font=("Arial", 20, "bold"),
                    text_color=colors["text"]).pack(pady=10)

        self.cpu_graph = AnimatedGraph(frame, "CPU Usage", colors["accent"], colors)
        self.ram_graph = AnimatedGraph(frame, "RAM Usage", colors["accent_light"], colors)
        self.disk_graph = AnimatedGraph(frame, "Disk Usage", colors["success"], colors)

        net_frame = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=10)
        net_frame.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(net_frame, text="Network Activity", font=("Arial", 12, "bold"),
                    text_color=colors["text"]).pack(pady=5)

        self.net_sent_label = ctk.CTkLabel(net_frame, text="Upload: 0 KB/s", text_color=colors["text_secondary"])
        self.net_sent_label.pack(side="left", padx=20, pady=5)
        self.net_recv_label = ctk.CTkLabel(net_frame, text="Download: 0 KB/s", text_color=colors["text_secondary"])
        self.net_recv_label.pack(side="right", padx=20, pady=5)

        self.last_net = psutil.net_io_counters()
        self.update_monitor()

    def update_monitor(self):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage(_system_root()).percent

            self.cpu_graph.update(cpu)
            self.ram_graph.update(ram)
            self.disk_graph.update(disk)

            current_net = psutil.net_io_counters()
            sent = (current_net.bytes_sent - self.last_net.bytes_sent) / 1024
            recv = (current_net.bytes_recv - self.last_net.bytes_recv) / 1024
            self.net_sent_label.configure(text=f"Upload: {sent:.1f} KB/s")
            self.net_recv_label.configure(text=f"Download: {recv:.1f} KB/s")
            self.last_net = current_net
        except:
            pass

        try:
            self.app.after(1000, self.update_monitor)
        except:
            pass
