import customtkinter as ctk
import os
import threading
import time
from pathlib import Path

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from .base_module import BaseModule
from .shared import ToolFrameContainer


class MusicModule(BaseModule):
    name = "Reproductor"
    icon = "🎵"
    description = "Reproductor de música con controles básicos"

    def __init__(self, app):
        super().__init__(app)
        self.music_dir = Path(app.exe_dir if hasattr(app, 'exe_dir') else os.getcwd()) / "music"
        self.music_dir.mkdir(exist_ok=True)
        self.current_track = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7
        self.playlist = []
        self.current_index = 0
        self._update_job = None
        self._destroying = False

        # Initialize pygame mixer if available
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            except Exception as e:
                print(f"Error initializing pygame mixer: {e}")
                self.pygame_available = False
        else:
            self.pygame_available = False

    def build(self, parent):
        self._build_tool_cards(parent, [
            ("Reproductor de Música", "Reproducir archivos de música locales", self.open_music_player, "🎵"),
            ("Gestionar Playlist", "Administrar tu colección de música", self.manage_playlist, "📋"),
        ])

    def open_music_player(self):
        self._destroying = False
        self._cancel_update_loop()
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Reproductor de Música", self.build, self.colors)
        win.pack(fill="both", expand=True)

        # Main container
        main_frame = ctk.CTkFrame(win, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Now playing section
        now_playing_frame = ctk.CTkFrame(main_frame, fg_color=self.colors["fg"], corner_radius=10)
        now_playing_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            now_playing_frame,
            text="🎵 Ahora sonando",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(pady=(15, 5))
        
        self.track_label = ctk.CTkLabel(
            now_playing_frame,
            text="Selecciona una pista para comenzar",
            font=("Arial", 14),
            text_color=self.colors["text_secondary"],
            wraplength=400
        )
        self.track_label.pack(pady=(0, 15))
        
        # Controls section
        controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        controls_frame.pack(fill="x", pady=10)
        
        # Control buttons
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(pady=10)
        
        self.prev_btn = ctk.CTkButton(
            button_frame,
            text="⏮️ Anterior",
            width=80,
            height=40,
            command=self.previous_track,
            fg_color=self.colors["fg"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"]
        )
        self.prev_btn.pack(side="left", padx=5)
        
        self.play_pause_btn = ctk.CTkButton(
            button_frame,
            text="▶️ Play",
            width=100,
            height=40,
            command=self.toggle_play_pause,
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"]
        )
        self.play_pause_btn.pack(side="left", padx=5)
        
        self.next_btn = ctk.CTkButton(
            button_frame,
            text="⏭️ Siguiente",
            width=80,
            height=40,
            command=self.next_track,
            fg_color=self.colors["fg"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"]
        )
        self.next_btn.pack(side="left", padx=5)
        
        # Progress bar
        progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_frame.pack(fill="x", pady=10, padx=20)
        
        self.progress_var = ctk.DoubleVar()
        self.progress_bar = ctk.CTkSlider(
            progress_frame,
            from_=0,
            to=100,
            variable=self.progress_var,
            command=self.seek_music,
            width=400
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.time_label = ctk.CTkLabel(
            progress_frame,
            text="00:00 / 00:00",
            width=80
        )
        self.time_label.pack(side="right")
        
        # Volume control
        volume_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        volume_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(volume_frame, text="🔊 Volumen:").pack(side="left", padx=(0, 10))
        
        self.volume_var = ctk.DoubleVar(value=self.volume * 100)
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=100,
            variable=self.volume_var,
            command=self.set_volume,
            width=200
        )
        self.volume_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.volume_label = ctk.CTkLabel(volume_frame, text="70%", width=40)
        self.volume_label.pack(side="right")
        
        # Playlist section
        playlist_frame = ctk.CTkFrame(main_frame, fg_color=self.colors["fg"], corner_radius=10)
        playlist_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        ctk.CTkLabel(
            playlist_frame,
            text="📋 Playlist",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        ).pack(pady=(15, 10))
        
        # Playlist listbox
        self.playlist_box = ctk.CTkTextbox(
            playlist_frame,
            height=200,
            fg_color=self.colors["bg"],
            text_color=self.colors["text"]
        )
        self.playlist_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Load initial playlist
        self.refresh_playlist()
        self._schedule_update_loop()

    def _cancel_update_loop(self):
        if self._update_job is not None:
            try:
                self.app.after_cancel(self._update_job)
            except Exception:
                pass
            self._update_job = None

    def _schedule_update_loop(self):
        self._cancel_update_loop()
        if self._destroying or not getattr(self.app, "winfo_exists", lambda: False)():
            return
        self._update_job = self.app.after(1000, self._check_music_state)

    def _check_music_state(self):
        if self._destroying or not getattr(self.app, "winfo_exists", lambda: False)():
            self._update_job = None
            return

        try:
            if PYGAME_AVAILABLE and self.pygame_available and self.is_playing and not self.is_paused:
                if not pygame.mixer.music.get_busy():
                    self.next_track()
        except Exception:
            pass

        self._schedule_update_loop()

    def refresh_playlist(self):
        """Refresh the playlist from the music directory"""
        self.playlist = []
        if self.music_dir.exists():
            for file_path in self.music_dir.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
                    self.playlist.append(file_path.name)

        self.update_playlist_display()

        # If we have tracks and none is selected, select the first one
        if self.playlist and self.current_index >= len(self.playlist):
            self.current_index = 0
            if self.playlist:
                self.load_track(self.playlist[self.current_index])

    def update_playlist_display(self):
        """Update the playlist display in the textbox"""
        if not hasattr(self, "playlist_box") or not self.playlist_box.winfo_exists():
            return

        self.playlist_box.delete("1.0", "end")
        if not self.playlist:
            self.playlist_box.insert("1.0", "No hay archivos de música en la carpeta 'music'\nColoca tus archivos .mp3, .wav, .ogg, etc. allí.")
            return

        for i, track in enumerate(self.playlist):
            prefix = "▶️ " if i == self.current_index else "  "
            self.playlist_box.insert("end", f"{prefix}{track}\n")

    def load_track(self, track_name):
        """Load a track for playback"""
        if not PYGAME_AVAILABLE or not self.pygame_available:
            self.app.toast.show("Reproductor no disponible", type="error")
            return
            
        track_path = self.music_dir / track_name
        if not track_path.exists():
            self.app.toast.show(f"Archivo no encontrado: {track_name}", type="error")
            return
            
        try:
            pygame.mixer.music.load(str(track_path))
            self.current_track = track_name
            self.is_playing = False
            self.is_paused = False
            self.update_track_label()
            self.app.toast.show(f"Cargado: {track_name}", type="info")
        except Exception as e:
            self.app.toast.show(f"Error al cargar pista: {str(e)}", type="error")

    def update_track_label(self):
        """Update the now playing label"""
        if not hasattr(self, "track_label") or not self.track_label.winfo_exists():
            return

        if self.current_track:
            # Clean up filename for display
            display_name = self.current_track.replace('.mp3', '').replace('.wav', '').replace('.ogg', '').replace('.flac', '').replace('.m4a', '')
            self.track_label.configure(text=display_name)
        else:
            self.track_label.configure(text="Selecciona una pista para comenzar")

    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if not PYGAME_AVAILABLE or not self.pygame_available:
            self.app.toast.show("Reproductor no disponible", type="error")
            return
            
        if not self.current_track and self.playlist:
            # Load first track if none selected
            self.load_track(self.playlist[0])
            self.current_index = 0
            self.update_playlist_display()
        
        if self.is_paused:
            # Resume
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            self.play_pause_btn.configure(text="⏸️ Pausa")
            self.app.toast.show("Reproduciendo", type="info")
        elif self.is_playing:
            # Pause
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self.play_pause_btn.configure(text="▶️ Play")
            self.app.toast.show("Pausado", type="info")
        else:
            # Start playing
            if self.current_track:
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.play_pause_btn.configure(text="⏸️ Pausa")
                self.app.toast.show(f"Reproduciendo: {self.current_track}", type="info")
            elif self.playlist:
                self.load_track(self.playlist[0])
                self.current_index = 0
                self.update_playlist_display()
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.play_pause_btn.configure(text="⏸️ Pausa")
                self.app.toast.show(f"Reproduciendo: {self.current_track}", type="info")

    def previous_track(self):
        """Play previous track"""
        if not self.playlist:
            return
            
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.load_track(self.playlist[self.current_index])
        self.update_playlist_display()
        
        if self.is_playing or self.is_paused:
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.play_pause_btn.configure(text="⏸️ Pausa")

    def next_track(self):
        """Play next track"""
        if not self.playlist:
            return
            
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.load_track(self.playlist[self.current_index])
        self.update_playlist_display()
        
        if self.is_playing or self.is_paused:
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.play_pause_btn.configure(text="⏸️ Pausa")

    def set_volume(self, value):
        """Set volume (0-100)"""
        self.volume = float(value) / 100
        if hasattr(self, "volume_label") and self.volume_label.winfo_exists():
            self.volume_label.configure(text=f"{int(float(value))}%")
        if PYGAME_AVAILABLE and self.pygame_available:
            pygame.mixer.music.set_volume(self.volume)

    def seek_music(self, value):
        """Seek to position in track (not fully implemented with pygame.mixer)"""
        # Note: pygame.mixer doesn't have precise seeking, this is a placeholder
        pass

    def on_deactivate(self):
        self._destroying = True
        self._cancel_update_loop()

    def manage_playlist(self):
        """Open playlist management window"""
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Gestionar Playlist", self.build, self.colors)
        win.pack(fill="both", expand=True)
        
        # Instructions
        ctk.CTkLabel(
            win,
            text="📁 Gestiona tu colección de música",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            win,
            text=f"Coloca tus archivos de música en: {self.music_dir}\nFormatos soportados: MP3, WAV, OGG, FLAC, M4A",
            font=("Arial", 12),
            text_color=self.colors["text_secondary"],
            justify="center"
        ).pack(pady=(0, 20))
        
        # Buttons
        button_frame = ctk.CTkFrame(win, fg_color="transparent")
        button_frame.pack(pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="📂 Abrir carpeta de música",
            command=self.open_music_folder,
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            width=180,
            height=40
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Actualizar lista",
            command=self.refresh_playlist,
            fg_color=self.colors["fg"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"],
            width=180,
            height=40
        ).pack(side="left", padx=10)
        
        # Current playlist display
        playlist_frame = ctk.CTkFrame(win, fg_color=self.colors["fg"], corner_radius=10)
        playlist_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            playlist_frame,
            text="🎵 Playlist actual",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        ).pack(pady=(15, 10))
        
        self.manage_playlist_box = ctk.CTkTextbox(
            playlist_frame,
            height=300,
            fg_color=self.colors["bg"],
            text_color=self.colors["text"]
        )
        self.manage_playlist_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.refresh_manage_playlist_display()

    def refresh_manage_playlist_display(self):
        """Refresh the playlist display in management view"""
        if not hasattr(self, "manage_playlist_box") or not self.manage_playlist_box.winfo_exists():
            return

        self.manage_playlist_box.delete("1.0", "end")
        if not self.playlist:
            self.manage_playlist_box.insert("1.0", "La playlist está vacía.\nAgrega archivos de música a la carpeta de música.")
            return

        for i, track in enumerate(self.playlist):
            self.manage_playlist_box.insert("end", f"{i+1}. {track}\n")

    def open_music_folder(self):
        """Open the music folder in file explorer"""
        import subprocess
        import platform
        
        folder_path = str(self.music_dir)
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            self.app.toast.show(f"Error al abrir carpeta: {str(e)}", type="error")


# Auto-register the module when imported
def register_music_module(app):
    from modules.module_manager import ModuleManager
    manager = ModuleManager(app)
    manager.register(MusicModule)
    return MusicModule