import customtkinter as ctk
import hashlib
import base64
import codecs
import time
import threading

from .base_module import BaseModule


class CryptoModule(BaseModule):
    name = "Cipher Deck"
    icon = "🔐"
    description = "Suite de herramientas criptográficas"

    def build(self, parent):
        colors = self.colors
        app = self.app

        header = ctk.CTkFrame(parent, fg_color=colors["fg"], corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="🔐 CRYPTOGRAPHIC CIPHER DECK", font=("Arial", 24, "bold"),
                    text_color=colors["text"]).pack(pady=15)

        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Left: Text Encryptor
        left_col = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        left_col.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(left_col, text="🔏 INTEGRATED TEXT ENCRYPTOR", font=("Arial", 14, "bold"), text_color=colors["accent"]).pack(pady=(15, 5))

        text_input = ctk.CTkTextbox(left_col, height=110, fg_color=colors["bg"], text_color=colors["text"])
        text_input.pack(fill="x", padx=20, pady=5)
        text_input.insert("1.0", "Mensaje táctico súper secreto...")

        opt_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        opt_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(opt_frame, text="ALGORITMO:", font=("Arial", 10, "bold"), text_color=colors["text_secondary"]).pack(side="left")
        cipher_combo = ctk.CTkComboBox(opt_frame, values=["Base64", "Caesar", "Rot13"], width=130)
        cipher_combo.pack(side="left", padx=10)
        cipher_combo.set("Base64")

        key_entry = ctk.CTkEntry(opt_frame, placeholder_text="Clave/Desplazamiento", fg_color=colors["bg"], width=120)
        key_entry.pack(side="right")
        key_entry.insert(0, "3")

        out_output = ctk.CTkTextbox(left_col, height=110, fg_color=colors["bg"], text_color=colors["accent_light"], font=("Consolas", 10))
        out_output.pack(fill="x", padx=20, pady=5)
        out_output.configure(state="disabled")

        def run_crypt(mode="encrypt"):
            raw = text_input.get("1.0", "end-1c")
            algo = cipher_combo.get()
            key_raw = key_entry.get()

            out = ""
            if algo == "Base64":
                try:
                    if mode == "encrypt":
                        out = base64.b64encode(raw.encode()).decode()
                    else:
                        out = base64.b64decode(raw.encode()).decode()
                except Exception as e:
                    out = f"[Error Base64]: {str(e)}"
            elif algo == "Rot13":
                out = codecs.encode(raw, 'rot_13')
            elif algo == "Caesar":
                try:
                    shift = int(key_raw) if mode == "encrypt" else -int(key_raw)
                    res = []
                    for char in raw:
                        if char.isalpha():
                            start = ord('A') if char.isupper() else ord('a')
                            res.append(chr((ord(char) - start + shift) % 26 + start))
                        else:
                            res.append(char)
                    out = "".join(res)
                except:
                    out = "[Error Caesar]: Desplazamiento debe ser entero"

            out_output.configure(state="normal")
            out_output.delete("1.0", "end")
            out_output.insert("1.0", out)
            out_output.configure(state="disabled")
            app.toast.show(f"Operación {algo} completada", type="success")

        btn_action_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(btn_action_frame, text="🔒 Cifrar", command=lambda: run_crypt("encrypt"), fg_color=colors["accent"], width=130).pack(side="left")
        ctk.CTkButton(btn_action_frame, text="🔓 Descifrar", command=lambda: run_crypt("decrypt"), fg_color=colors["accent_light"], width=130).pack(side="right")

        # Right: Hash Generator & Cracker
        right_col = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        right_col.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(right_col, text="🔐 SECURE MULTI-HASH GENERATOR", font=("Arial", 14, "bold"), text_color=colors["accent_light"]).pack(pady=(15, 5))
        hash_input = ctk.CTkEntry(right_col, placeholder_text="Texto a hashear...", fg_color=colors["bg"], height=35)
        hash_input.pack(fill="x", padx=20, pady=5)

        hash_output = ctk.CTkTextbox(right_col, height=120, fg_color=colors["bg"], text_color=colors["text_secondary"], font=("Consolas", 9))
        hash_output.pack(fill="x", padx=20, pady=5)
        hash_output.configure(state="disabled")

        def generate_hashes():
            text = hash_input.get()
            if not text:
                return
            m5 = hashlib.md5(text.encode()).hexdigest()
            s256 = hashlib.sha256(text.encode()).hexdigest()
            s512 = hashlib.sha512(text.encode()).hexdigest()

            hash_output.configure(state="normal")
            hash_output.delete("1.0", "end")
            hash_output.insert("1.0", f"MD5: {m5}\n\nSHA-256: {s256}\n\nSHA-512: {s512}")
            hash_output.configure(state="disabled")
            app.toast.show("Hashes generados correctamente", type="success")

        ctk.CTkButton(right_col, text="⚡ Generar Hashes", command=generate_hashes, fg_color=colors["accent_light"]).pack(pady=5, padx=20, fill="x")

        # Hash Cracker
        ctk.CTkLabel(right_col, text="💀 DICTIONARY HASH CRACKER", font=("Arial", 14, "bold"), text_color=colors["accent_light"]).pack(pady=(15, 5))
        crack_input = ctk.CTkEntry(right_col, placeholder_text="Hash MD5 a crackear...", fg_color=colors["bg"], height=35)
        crack_input.pack(fill="x", padx=20, pady=5)
        crack_input.insert(0, "098f6bcd4621d373cade4e832627b4f6")

        crack_output = ctk.CTkTextbox(right_col, height=110, fg_color=colors["bg"], text_color="#ff5555", font=("Consolas", 10))
        crack_output.pack(fill="x", padx=20, pady=5)
        crack_output.insert("1.0", "[crack-system]: listo para ataque de diccionario...")
        crack_output.configure(state="disabled")

        def run_crack():
            h = crack_input.get().strip()
            if not h:
                return
            crack_output.configure(state="normal")
            crack_output.delete("1.0", "end")
            crack_output.insert("end", f"[!] Iniciando ataque de diccionario...\n[!] MD5 Hash objetivo: {h}\n\n")
            crack_output.configure(state="disabled")
            app.toast.show("Iniciando ataque de fuerza bruta...", type="warning")

            def run():
                common_passwords = ["123456", "password", "123456789", "12345678", "12345", "qwerty", "secret", "admin", "test", "welcome", "letmein", "superman", "hacker", "nethub"]
                cracked = False
                for pw in common_passwords:
                    time.sleep(0.08)
                    calc = hashlib.md5(pw.encode()).hexdigest()
                    crack_output.configure(state="normal")
                    crack_output.insert("end", f"  • Intentando: '{pw}' -> {calc[:16]}...\n")
                    crack_output.see("end")
                    crack_output.configure(state="disabled")
                    if calc == h:
                        crack_output.configure(state="normal")
                        crack_output.insert("end", f"\n🎉 CRACKEADO CON ÉXITO!\n🎉 Palabrasecreta: '{pw}'")
                        crack_output.configure(state="disabled")
                        app.toast.show(f"Hash crackeado: '{pw}'", type="success")
                        cracked = True
                        break
                if not cracked:
                    crack_output.configure(state="normal")
                    crack_output.insert("end", "\n❌ ERROR: Hash no encontrado en diccionario base.")
                    crack_output.configure(state="disabled")
                    app.toast.show("Ataque fallido", type="error")
            threading.Thread(target=run, daemon=True).start()
