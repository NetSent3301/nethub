import customtkinter as ctk
import time
import random
import platform
import threading
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class ToolFrameContainer(ctk.CTkFrame):
    def __init__(self, parent, title, back_cmd, colors):
        super().__init__(parent, fg_color="transparent")
        self.colors = colors
        self.back_cmd = back_cmd
        self.is_tool_container = True
        self.auto_back = True

        header = ctk.CTkFrame(self, fg_color=colors["fg"], corner_radius=15, height=60)
        header.pack(fill="x", padx=15, pady=(15, 10))

        try:
            self.winfo_toplevel().play_sound("click")
        except:
            pass

        back_btn = ctk.CTkButton(header, text="⬅ VOLVER A LA SUITE", command=back_cmd,
                                 fg_color=colors["hover"], hover_color=colors["accent"],
                                 text_color="white", font=("Arial", 11, "bold"), width=160, height=38,
                                 corner_radius=8)
        back_btn.pack(side="left", padx=12, pady=10)

        title_lbl = ctk.CTkLabel(header, text=title.upper(), font=("Arial", 16, "bold"), text_color=colors["accent_light"])
        title_lbl.pack(side="left", padx=15, pady=10)

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=15, pady=10)

        self.led_canvas = ctk.CTkCanvas(status_frame, width=12, height=12, bg=colors["fg"], highlightthickness=0)
        self.led_canvas.pack(side="left", padx=(0, 8))
        self.led_oval = self.led_canvas.create_oval(1, 1, 11, 11, fill="#3acc3a", outline="")

        self.led_state = True
        def blink_led():
            if not self.winfo_exists() or not self.led_canvas.winfo_exists():
                return
            self.led_state = not self.led_state
            color = "#3acc3a" if self.led_state else "#1a4a1a"
            self.led_canvas.itemconfig(self.led_oval, fill=color)
            self.after(500, blink_led)

        blink_led()

        status_lbl = ctk.CTkLabel(status_frame, text="⚡ SYSTEM CORE ACTIVE", font=("Arial", 10, "bold"), text_color=colors["text"])
        status_lbl.pack(side="right")

    def title(self, *args, **kwargs):
        pass

    def geometry(self, *args, **kwargs):
        pass

    def protocol(self, *args, **kwargs):
        pass

    def destroy(self):
        if getattr(self, 'auto_back', True):
            self.back_cmd()
        else:
            super().destroy()


class AnimatedGraph(ctk.CTkFrame):
    def __init__(self, parent, title, color, colors):
        super().__init__(parent, fg_color=colors["fg"], corner_radius=10)
        self.colors = colors
        self.title = title
        self.color = color
        self.data = deque([0] * 60, maxlen=60)

        self.pack(fill="x", pady=8, padx=10)

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(title_frame, text=title, font=("Arial", 12, "bold"),
                    text_color=colors["text"]).pack(side="left")
        self.value_label = ctk.CTkLabel(title_frame, text="0%", font=("Arial", 12),
                                        text_color=colors["accent"])
        self.value_label.pack(side="right")

        self.fig = Figure(figsize=(7, 1.5), facecolor=colors["fg"], dpi=80)
        self.fig.patch.set_facecolor(colors["fg"])
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(colors["fg"])
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, 60)
        self.ax.tick_params(colors=colors["text_secondary"], labelbottom=False, labelleft=False)
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.line, = self.ax.plot(range(60), [0]*60, color=color, linewidth=2)
        self.ax.fill_between(range(60), [0]*60, [0]*60, color=color, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="x", padx=5, pady=5)

    def update(self, value):
        self.data.append(value)
        self.line.set_ydata(list(self.data))
        self.ax.fill_between(range(60), 0, list(self.data), color=self.color, alpha=0.3)
        self.value_label.configure(text=f"{value:.1f}%")
        self.canvas.draw_idle()
