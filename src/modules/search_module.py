import customtkinter as ctk
import json
import threading
import requests
import urllib.parse

from .base_module import BaseModule


class SearchModule(BaseModule):
    name = "Web Search"
    icon = "🌐"
    description = "Búsqueda en internet integrada"

    def build(self, parent):
        colors = self.colors
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        header = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=10)
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Búsqueda en Internet",
                     font=("Arial", 20, "bold"), text_color=colors["text"]).pack(pady=15)

        search_row = ctk.CTkFrame(frame, fg_color="transparent")
        search_row.pack(fill="x", pady=5)

        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Buscar en internet...",
                                          fg_color=colors["bg"], text_color=colors["text"],
                                          height=40, font=("Arial", 14))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        self.search_btn = ctk.CTkButton(search_row, text="Buscar", command=self._do_search,
                                         fg_color=colors["accent"], width=100, height=40)
        self.search_btn.pack(side="right")

        # Engine selector
        engine_row = ctk.CTkFrame(frame, fg_color="transparent")
        engine_row.pack(fill="x", pady=4)
        self.engine_var = ctk.StringVar(value="duckduckgo")
        for eng, label in [("duckduckgo", "DuckDuckGo"), ("google", "Google (lite)")]:
            ctk.CTkRadioButton(engine_row, text=label, variable=self.engine_var, value=eng,
                               fg_color=colors["accent"], text_color=colors["text"]).pack(side="left", padx=8)

        self.status_label = ctk.CTkLabel(frame, text="", font=("Arial", 10),
                                          text_color=colors["text_secondary"])
        self.status_label.pack(anchor="w", pady=2)

        self.results_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, pady=5)

        # History
        history_frame = ctk.CTkFrame(frame, fg_color="transparent")
        history_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(history_frame, text="Historial:", font=("Arial", 10),
                     text_color=colors["text_secondary"]).pack(side="left")
        self.history_list = []
        ctk.CTkButton(history_frame, text="Limpiar", command=self._clear_history,
                      fg_color="transparent", hover_color=colors["hover"],
                      text_color=colors["text_secondary"], width=60, height=24,
                      font=("Arial", 9)).pack(side="right")

    def _do_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        engine = self.engine_var.get()
        self.status_label.configure(text="Buscando...")
        self.search_btn.configure(state="disabled")

        # Add to history
        if query not in self.history_list:
            self.history_list.insert(0, query)
            if len(self.history_list) > 10:
                self.history_list.pop()

        # Clear results
        for w in self.results_frame.winfo_children():
            w.destroy()

        threading.Thread(target=self._search_worker, args=(query, engine), daemon=True).start()

    def _search_worker(self, query, engine):
        try:
            if engine == "duckduckgo":
                results = self._search_duckduckgo(query)
            else:
                results = self._search_google_lite(query)

            def render():
                if not self.results_frame.winfo_exists():
                    return
                self.search_btn.configure(state="normal")
                if not results:
                    self.status_label.configure(text="Sin resultados")
                    ctk.CTkLabel(self.results_frame, text="No se encontraron resultados",
                                 font=("Arial", 12), text_color=self.colors["text_secondary"]).pack(pady=30)
                    return
                self.status_label.configure(text=f"{len(results)} resultados")
                for r in results:
                    self._add_result_card(r)

            self.app.after(0, render)

            # Notify
            self.app.notify(f"Búsqueda: {query[:40]}",
                            f"{len(results)} resultados encontrados",
                            category="general", priority="low", source="search")

        except Exception as e:
            self.app.after(0, lambda: self.status_label.configure(text=f"Error: {e}"))
            self.app.after(0, lambda: self.search_btn.configure(state="normal"))

    def _search_duckduckgo(self, query):
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=10)
        results = []
        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_result = False
                self.in_link = False
                self.in_snippet = False
                self.current = {}
                self.results = []
                self._tag_stack = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("class") == "result-link":
                    self.in_link = True
                    self.current["url"] = attrs.get("href", "")
                    self.current["title"] = ""
                elif tag == "td" and attrs.get("class") == "result-snippet":
                    self.in_snippet = True
                    self.current["snippet"] = ""

            def handle_data(self, data):
                if self.in_link:
                    self.current["title"] = (self.current.get("title", "") + data).strip()
                if self.in_snippet:
                    self.current["snippet"] = (self.current.get("snippet", "") + data).strip()

            def handle_endtag(self, tag):
                if tag == "a" and self.in_link:
                    self.in_link = False
                    if self.current.get("title"):
                        self.results.append(self.current.copy())
                    self.current = {}
                if tag == "td" and self.in_snippet:
                    self.in_snippet = False

        parser = DDGParser()
        parser.feed(r.text)
        for res in parser.results[:15]:
            results.append({
                "title": res.get("title", ""),
                "url": res.get("url", ""),
                "snippet": res.get("snippet", ""),
            })
        return results

    def _search_google_lite(self, query):
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        results = []
        import re
        # Minimal parsing: extract <h3> as title, parent <a> as link
        for match in re.finditer(r'<h3[^>]*>(.*?)</h3>', r.text, re.DOTALL):
            title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if title:
                results.append({"title": title, "url": "", "snippet": ""})
                if len(results) >= 15:
                    break
        return results

    def _add_result_card(self, result):
        colors = self.colors
        card = ctk.CTkFrame(self.results_frame, fg_color=colors["fg"], corner_radius=8)
        card.pack(fill="x", pady=3, padx=2)

        ctk.CTkLabel(card, text=result.get("title", ""),
                     font=("Arial", 13, "bold"), text_color=colors["text"],
                     anchor="w").pack(anchor="w", padx=15, pady=(8, 2))

        if result.get("url"):
            ctk.CTkLabel(card, text=result["url"],
                         font=("Arial", 9), text_color=colors["accent"],
                         anchor="w").pack(anchor="w", padx=15)

        if result.get("snippet"):
            ctk.CTkLabel(card, text=result["snippet"],
                         font=("Arial", 10), text_color=colors["text_secondary"],
                         anchor="w", wraplength=600, justify="left").pack(anchor="w", padx=15, pady=(2, 8))

        if result.get("url"):
            import webbrowser
            ctk.CTkButton(card, text="Abrir", command=lambda u=result["url"]: webbrowser.open(u),
                          fg_color="transparent", hover_color=colors["hover"],
                          text_color=colors["accent"], width=60, height=26,
                          font=("Arial", 9)).pack(anchor="e", padx=10, pady=(0, 6))

    def _clear_history(self):
        self.history_list.clear()
        self.app.toast.show("Historial limpiado", type="info")

    def on_activate(self):
        if self.search_entry:
            self.search_entry.focus()
