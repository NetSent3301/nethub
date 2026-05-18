import customtkinter as ctk
import socket
import threading
import time
import requests
import json

from .base_module import BaseModule


class OSINTModule(BaseModule):
    name = "OSINT & DarkNet"
    icon = "🌐"
    description = "Reconocimiento OSINT y DarkNet"

    def build(self, parent):
        colors = self.colors
        app = self.app

        header = ctk.CTkFrame(parent, fg_color=colors["fg"], corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="🌐 OSINT & DARKNET RECON", font=("Arial", 24, "bold"),
                    text_color=colors["text"]).pack(pady=15)

        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Left Column: IP Tracker
        left_col = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        left_col.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(left_col, text="🛰️ TACTICAL IP GEOLOCATION", font=("Arial", 14, "bold"), text_color=colors["accent"]).pack(pady=(15, 5))
        ip_entry = ctk.CTkEntry(left_col, placeholder_text="Ingrese IP de objetivo (ej: 8.8.8.8)", fg_color=colors["bg"], height=35)
        ip_entry.pack(fill="x", padx=20, pady=5)

        ip_output = ctk.CTkTextbox(left_col, height=140, fg_color=colors["bg"], text_color=colors["text_secondary"], font=("Consolas", 10))
        ip_output.pack(fill="x", padx=20, pady=5)
        ip_output.insert("1.0", "🛰️ AGENTE SATELITAL: Listo para triangulación...")
        ip_output.configure(state="disabled")

        def trace_ip():
            ip = ip_entry.get().strip()
            if not ip:
                app.toast.show("Por favor ingrese una dirección IP", type="error")
                return
            ip_output.configure(state="normal")
            ip_output.delete("1.0", "end")
            ip_output.insert("end", f"🛰️ [OSINT] Conectando con nodos satelitales...\n🛰️ [OSINT] Geolocalizando IP objetivo: {ip}\n")
            ip_output.configure(state="disabled")
            app.toast.show("Rastreando IP...", type="info")

            def run():
                time.sleep(1.2)
                try:
                    res = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                    data = res.json()
                    ip_output.configure(state="normal")
                    if data.get("status") == "success":
                        out = f"🛰️ TRIANGULACIÓN COMPLETADA:\n"
                        out += f"  • PAÍS: {data.get('country', 'N/A')} ({data.get('countryCode', 'N/A')})\n"
                        out += f"  • CIUDAD/ESTADO: {data.get('city', 'N/A')} / {data.get('regionName', 'N/A')}\n"
                        out += f"  • PROVEEDOR (ISP): {data.get('isp', 'N/A')}\n"
                        out += f"  • LATITUD / LONGITUD: {data.get('lat', 'N/A')} / {data.get('lon', 'N/A')}\n"
                        out += f"  • RANGO CIDR: {data.get('query', 'N/A')}\n"
                        out += f"  • RIESGO ESTIMADO: BAJO/MEDIO"
                    else:
                        out = f"⚠️ ERROR DE TRIANGULACIÓN:\n  • {data.get('message', 'IP no válida o reservada')}"
                    ip_output.insert("end", out)
                    ip_output.configure(state="disabled")
                    app.toast.show("Triangulación exitosa", type="success")
                except Exception as e:
                    ip_output.configure(state="normal")
                    ip_output.insert("end", f"❌ ERROR DE RED:\n  • {str(e)}")
                    ip_output.configure(state="disabled")
                    app.toast.show("Error al consultar IP", type="error")
            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(left_col, text="⚡ Iniciar Geolocalización", command=trace_ip, fg_color=colors["accent"]).pack(pady=10, padx=20, fill="x")

        # Subdomain Enumerator
        ctk.CTkLabel(left_col, text="🔍 SUBDOMAIN ENUMERATOR", font=("Arial", 14, "bold"), text_color=colors["accent"]).pack(pady=(15, 5))
        dom_entry = ctk.CTkEntry(left_col, placeholder_text="Dominio objetivo (ej: google.com)", fg_color=colors["bg"], height=35)
        dom_entry.pack(fill="x", padx=20, pady=5)

        dom_output = ctk.CTkTextbox(left_col, height=140, fg_color=colors["bg"], text_color="#3acc3a", font=("Consolas", 10))
        dom_output.pack(fill="x", padx=20, pady=5)
        dom_output.insert("1.0", "[recon-bot] listo para enumerar...")
        dom_output.configure(state="disabled")

        def start_subdomain_enum():
            dom = dom_entry.get().strip()
            if not dom:
                app.toast.show("Ingrese un dominio", type="error")
                return
            dom_output.configure(state="normal")
            dom_output.delete("1.0", "end")
            dom_output.insert("end", f"[$] recon-bot -d {dom}\n[$] Cargando wordlist táctica de subdominios...\n[$] Escaneando DNS records en cascada...\n\n")
            dom_output.configure(state="disabled")
            app.toast.show("Enumerando subdominios...", type="info")

            def run():
                common = ["www", "mail", "ftp", "admin", "dev", "api", "vpn", "portal", "stage", "shop", "blog", "secure", "db", "cloud", "ns1", "ns2", "test", "support"]
                found = []
                for sub in common:
                    time.sleep(0.1)
                    full = f"{sub}.{dom}"
                    try:
                        socket.gethostbyname(full)
                        found.append(full)
                        dom_output.configure(state="normal")
                        dom_output.insert("end", f"  [+] DETECTADO: {full}\n")
                        dom_output.see("end")
                        dom_output.configure(state="disabled")
                    except:
                        pass
                dom_output.configure(state="normal")
                dom_output.insert("end", f"\n[!] ESCANEO COMPLETADO. Se detectaron {len(found)} subdominios activos.")
                dom_output.configure(state="disabled")
                app.toast.show("Enumeración DNS finalizada", type="success")
            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(left_col, text="⚡ Buscar Subdominios", command=start_subdomain_enum, fg_color=colors["accent"]).pack(pady=10, padx=20, fill="x")

        # Right Column: OSINT User Stalker
        right_col = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        right_col.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(right_col, text="🕵️ OSINT USERNAME STALKER", font=("Arial", 14, "bold"), text_color=colors["accent_light"]).pack(pady=(15, 5))
        user_entry = ctk.CTkEntry(right_col, placeholder_text="Apodo/Username a buscar (ej: ghost_coder)", fg_color=colors["bg"], height=35)
        user_entry.pack(fill="x", padx=20, pady=5)

        stalk_output = ctk.CTkTextbox(right_col, height=390, fg_color=colors["bg"], text_color=colors["text"], font=("Consolas", 10))
        stalk_output.pack(fill="both", expand=True, padx=20, pady=5)
        stalk_output.insert("1.0", "🕵️ STALKER SYSTEM: Esperando firma digital...")
        stalk_output.configure(state="disabled")

        def stalk_user():
            usr = user_entry.get().strip()
            if not usr:
                app.toast.show("Por favor ingrese un username", type="error")
                return
            stalk_output.configure(state="normal")
            stalk_output.delete("1.0", "end")
            stalk_output.insert("end", f"🕵️ [STALKER] Iniciando escaneo global para alias: {usr}\n🕵️ [STALKER] Buscando en bases de datos OSINT indexadas...\n🕵️ [STALKER] Comprobando huella digital de red...\n\n")
            stalk_output.configure(state="disabled")
            app.toast.show("Buscando huellas de usuario...", type="info")

            def run():
                platforms = [
                    ("GitHub", f"https://github.com/{usr}"),
                    ("Twitter/X", f"https://x.com/{usr}"),
                    ("Reddit", f"https://reddit.com/user/{usr}"),
                    ("Medium", f"https://medium.com/@{usr}"),
                    ("GitLab", f"https://gitlab.com/{usr}"),
                    ("Pinterest", f"https://pinterest.com/{usr}"),
                    ("Steam", f"https://steamcommunity.com/id/{usr}"),
                ]

                count = 0
                for plat, url in platforms:
                    time.sleep(0.12)
                    try:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        res = requests.head(url, headers=headers, timeout=3)
                        status = res.status_code
                    except:
                        status = 404

                    stalk_output.configure(state="normal")
                    if status == 200:
                        count += 1
                        stalk_output.insert("end", f"  🟢 ENCONTRADO en {plat}:\n     🔗 {url}\n\n")
                    else:
                        stalk_output.insert("end", f"  🔴 No detectado en {plat}\n")
                    stalk_output.see("end")
                    stalk_output.configure(state="disabled")

                stalk_output.configure(state="normal")
                stalk_output.insert("end", f"\n[!] BÚSQUEDA OSINT FINALIZADA.\n[!] Cuenta(s) confirmada(s): {count} de {len(platforms)} plataformas analizadas.")
                stalk_output.configure(state="disabled")
                app.toast.show(f"Análisis OSINT listo, {count} coincidencias", type="success")

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(right_col, text="🕵️ Rastrear Huella Digital", command=stalk_user, fg_color=colors["accent_light"]).pack(pady=15, padx=20, fill="x")
