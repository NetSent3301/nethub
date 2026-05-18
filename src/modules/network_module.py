import customtkinter as ctk
import socket
import subprocess
import threading
import time
import platform
import requests
import json

from .base_module import BaseModule
from .shared import ToolFrameContainer


class NetworkModule(BaseModule):
    name = "Signals Recon"
    icon = "📡"
    description = "Inteligencia de redes y resolución de dominios"

    def build(self, parent):
        self._build_tool_cards(parent, [
            ("Ping Monitor", "Monitoreo ICMP en tiempo real", self.ping_monitor, "📶"),
            ("DNS Lookup", "Resolución de dominios y registros", self.dns_lookup, "🌐"),
            ("GeoIP Tracker", "Geolocalización de direcciones IP", self.geoip, "📍"),
            ("Bandwidth Test", "Prueba de velocidad de conexión", self.bandwidth_test, "⚡"),
        ])

    def ping_monitor(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Ping Monitor", self.build, self.colors)
        win.pack(fill="both", expand=True)

        target = ctk.CTkEntry(win, placeholder_text="IP o dominio", width=300)
        target.pack(pady=10)
        output = ctk.CTkTextbox(win, height=280)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        running = True

        def start():
            ip = target.get()
            if not ip:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Monitoreando {ip}...\n")

            def run():
                nonlocal running
                running = True
                while running:
                    if not win.winfo_exists() or not output.winfo_exists():
                        break
                    cmd = f"ping -n 1 {ip}" if platform.system() == "Windows" else f"ping -c 1 {ip}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if not win.winfo_exists() or not output.winfo_exists():
                        break
                    lines = result.stdout.split('\n')
                    ping_line = next((l for l in lines if any(x in l.lower() for x in ["bytes=", "tiempo=", "time=", "perdidos", "lost"])), lines[1] if len(lines) > 1 else "")
                    app.after(0, lambda pl=ping_line: output.winfo_exists() and (output.insert("end", pl + "\n") or output.see("end")))
                    time.sleep(1)

            threading.Thread(target=run, daemon=True).start()

        def stop():
            nonlocal running
            running = False

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Iniciar", command=start, fg_color=self.colors["accent"], width=140).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Detener", command=stop, fg_color="red", width=140).pack(side="left", padx=10)

    def dns_lookup(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "DNS Lookup", self.build, self.colors)
        win.pack(fill="both", expand=True)

        domain = ctk.CTkEntry(win, placeholder_text="Dominio", width=300)
        domain.pack(pady=10)
        output = ctk.CTkTextbox(win, height=250)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def lookup():
            d = domain.get()
            if not d:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Resolviendo {d}...\n\n")
            try:
                ips = socket.gethostbyname_ex(d)
                output.insert("end", f"  [+] Canónico: {ips[0]}\n")
                output.insert("end", f"  [+] Aliases: {', '.join(ips[1]) if ips[1] else 'Ninguno'}\n")
                output.insert("end", f"  [+] IPs:\n")
                for ip in ips[2]:
                    output.insert("end", f"      - {ip}\n")
                app.toast.show("DNS resuelto", type="success")
            except:
                output.insert("end", "❌ Error al resolver el dominio.")
                app.toast.show("Error DNS", type="error")

        ctk.CTkButton(win, text="Resolver", command=lookup, fg_color=self.colors["accent"]).pack(pady=10)

    def geoip(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "GeoIP Tracker", self.build, self.colors)
        win.pack(fill="both", expand=True)

        ip_entry = ctk.CTkEntry(win, placeholder_text="Dirección IP", width=300)
        ip_entry.pack(pady=10)
        output = ctk.CTkTextbox(win, height=280)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def lookup():
            ip = ip_entry.get()
            output.delete("1.0", "end")
            output.insert("end", f"Localizando {ip}...\n")

            def run():
                try:
                    response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                    data = response.json()
                    app.after(0, lambda: output.insert("end", json.dumps(data, indent=2)))
                    app.after(0, lambda: app.toast.show("GeoIP completado", type="success"))
                except:
                    app.after(0, lambda: output.insert("end", "Error al consultar GeoIP."))
                    app.after(0, lambda: app.toast.show("Error GeoIP", type="error"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="Consultar", command=lookup, fg_color=self.colors["accent"]).pack(pady=10)

    def bandwidth_test(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Bandwidth Test", self.build, self.colors)
        win.pack(fill="both", expand=True)

        result_label = ctk.CTkLabel(win, text="Presiona para iniciar la prueba", font=("Arial", 14, "bold"))
        result_label.pack(pady=30)

        progress = ctk.CTkProgressBar(win, progress_color=self.colors["accent"])
        progress.pack(fill="x", padx=40, pady=20)
        progress.set(0)

        def test():
            result_label.configure(text="⚡ Descargando archivo de prueba...")
            progress.set(0)

            def run():
                try:
                    start = time.time()
                    response = requests.get("http://speedtest.tele2.net/10MB.zip", stream=True, timeout=15)
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=32768):
                        if not win.winfo_exists():
                            return
                        downloaded += len(chunk)
                        app.after(0, lambda val=float(downloaded)/10_485_760: progress.set(min(val, 1.0)))
                    elapsed = time.time() - start
                    speed = (downloaded * 8) / (elapsed * 1_000_000)
                    app.after(0, lambda: result_label.configure(text=f"🚀 {speed:.2f} Mbps"))
                    app.after(0, lambda: app.toast.show(f"Test: {speed:.2f} Mbps", type="success"))
                except:
                    app.after(0, lambda: result_label.configure(text="❌ Error en la prueba."))
                    app.after(0, lambda: app.toast.show("Error de conexión", type="error"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="Probar Velocidad", command=test, fg_color=self.colors["accent"]).pack(pady=10)
