import customtkinter as ctk
from .base_module import BaseModule
import random
import time


class SandBoxModule(BaseModule):
    name = "Caja de Arena"
    icon = "🏜️"
    description = "Arena con físicas simples"

    GRID_WIDTH = 140
    GRID_HEIGHT = 80
    CELL_SIZE = 8

    EMPTY = 0
    SAND = 1

    def build(self, parent):
        self.content_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )
        self.content_frame.pack(fill="both", expand=True)

        title = ctk.CTkLabel(
            self.content_frame,
            text="🏜️ Caja de Arena",
            font=("Arial", 24, "bold")
        )
        title.pack(pady=(15, 5))

        self.stats_label = ctk.CTkLabel(
            self.content_frame,
            text="Partículas: 0 | FPS: 0",
            font=("Arial", 13)
        )
        self.stats_label.pack()

        self.canvas = ctk.CTkCanvas(
            self.content_frame,
            width=self.GRID_WIDTH * self.CELL_SIZE,
            height=self.GRID_HEIGHT * self.CELL_SIZE,
            bg="#111111",
            highlightthickness=0
        )
        self.canvas.pack(pady=10)

        controls = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent"
        )
        controls.pack(pady=5)

        ctk.CTkButton(
            controls,
            text="🧹 Limpiar",
            command=self.clear_grid
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            controls,
            text="💥 Explosión",
            command=self.spawn_random
        ).pack(side="left", padx=5)

        self.grid = [
            [self.EMPTY for _ in range(self.GRID_WIDTH)]
            for _ in range(self.GRID_HEIGHT)
        ]

        self.mouse_down = False
        self.last_time = time.time()
        self.frames = 0
        self.fps = 0

        self.canvas.bind("<ButtonPress-1>", self.mouse_press)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)

        self.update_simulation()

    def mouse_press(self, event):
        self.mouse_down = True
        self.place_sand(event)

    def mouse_release(self, event):
        self.mouse_down = False

    def mouse_drag(self, event):
        if self.mouse_down:
            self.place_sand(event)

    def place_sand(self, event):
        x = event.x // self.CELL_SIZE
        y = event.y // self.CELL_SIZE

        radius = 2

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx = x + dx
                ny = y + dy

                if (
                    0 <= nx < self.GRID_WIDTH
                    and 0 <= ny < self.GRID_HEIGHT
                ):
                    self.grid[ny][nx] = self.SAND

    def update_simulation(self):
        # Física de abajo hacia arriba
        for y in range(self.GRID_HEIGHT - 2, -1, -1):
            for x in range(self.GRID_WIDTH):

                if self.grid[y][x] == self.SAND:

                    # Abajo
                    if self.grid[y + 1][x] == self.EMPTY:
                        self.grid[y][x] = self.EMPTY
                        self.grid[y + 1][x] = self.SAND

                    else:
                        direction = random.choice([-1, 1])

                        nx = x + direction

                        if (
                            0 <= nx < self.GRID_WIDTH
                            and self.grid[y + 1][nx] == self.EMPTY
                        ):
                            self.grid[y][x] = self.EMPTY
                            self.grid[y + 1][nx] = self.SAND

        self.render()

        self.frames += 1
        current = time.time()

        if current - self.last_time >= 1:
            self.fps = self.frames
            self.frames = 0
            self.last_time = current

        self.stats_label.configure(
            text=f"Partículas: {self.count_particles()} | FPS: {self.fps}"
        )

        self.content_frame.after(16, self.update_simulation)

    def render(self):
        self.canvas.delete("all")

        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):

                if self.grid[y][x] == self.SAND:
                    px = x * self.CELL_SIZE
                    py = y * self.CELL_SIZE

                    self.canvas.create_rectangle(
                        px,
                        py,
                        px + self.CELL_SIZE,
                        py + self.CELL_SIZE,
                        fill="#d8b56a",
                        outline=""
                    )

    def clear_grid(self):
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                self.grid[y][x] = self.EMPTY

    def spawn_random(self):
        for _ in range(800):
            x = random.randint(0, self.GRID_WIDTH - 1)
            y = random.randint(0, 20)

            self.grid[y][x] = self.SAND

    def count_particles(self):
        return sum(
            row.count(self.SAND)
            for row in self.grid
        )

    def on_activate(self):
        print("[SAND BOX] Activado")

    def on_deactivate(self):
        print("[SAND BOX] Desactivado")