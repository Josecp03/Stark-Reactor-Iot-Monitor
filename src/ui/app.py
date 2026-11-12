"""Ventana principal de Stark Reactor IoT Monitor (P4-01).

Estructura base de la interfaz:
- Cabecera con el canal configurado.
- Aviso de configuración cuando faltan variables obligatorias.
- Pestaña "Enviar muestra" (formulario manual, issue #15).
- Pestaña "Histórico" (tabla de registros, issue #16).
- Barra de estado.
"""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Sequence
from tkinter import messagebox, ttk

from src.config import ConfigProblem, ThingSpeakConfig

APP_TITLE = "Stark Reactor IoT Monitor"
CHANNEL_URL_TEMPLATE = "https://thingspeak.mathworks.com/channels/{channel_id}"


class ReactorMonitorApp(tk.Tk):
    """Ventana principal de la aplicación."""

    def __init__(self, config: ThingSpeakConfig, problems: Sequence[ConfigProblem] = ()) -> None:
        super().__init__()
        self.config_data = config
        self.problems = list(problems)
        self.status_var = tk.StringVar()

        self.title(APP_TITLE)
        self.geometry("960x620")
        self.minsize(760, 480)

        self._build_header()
        if self.problems:
            self._build_config_warning()
        self._build_tabs()
        self._build_status_bar()

        self.set_status(self._initial_status())

    # --- Construcción de la interfaz -------------------------------------------------

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill=tk.X)
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            header,
            text=f"Canal ThingSpeak {self.config_data.channel_id} · "
            + CHANNEL_URL_TEMPLATE.format(channel_id=self.config_data.channel_id),
        ).pack(anchor=tk.W)

    def _build_config_warning(self) -> None:
        box = tk.Frame(self, bg="#fff4ce", highlightbackground="#e0b800", highlightthickness=1)
        box.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(
            box,
            text="Configuración incompleta",
            bg="#fff4ce",
            fg="#5c4400",
            font=("Segoe UI", 10, "bold"),
            anchor=tk.W,
        ).pack(fill=tk.X, padx=10, pady=(6, 0))
        for problem in self.problems:
            tk.Label(
                box,
                text=f"• {problem.message}",
                bg="#fff4ce",
                fg="#5c4400",
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=880,
            ).pack(fill=tk.X, padx=10, pady=(2, 6))

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        self.write_tab = ttk.Frame(notebook, padding=16)
        self.history_tab = ttk.Frame(notebook, padding=16)
        notebook.add(self.write_tab, text="Enviar muestra")
        notebook.add(self.history_tab, text="Histórico")

        # Contenido provisional hasta implementar #15 y #16.
        ttk.Label(self.write_tab, text="Formulario de entrada manual (pendiente, issue #15).").pack(
            anchor=tk.W
        )
        ttk.Label(self.history_tab, text="Tabla de histórico (pendiente, issue #16).").pack(anchor=tk.W)

    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self, padding=(16, 4))
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(bar, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X)

    # --- Estado ----------------------------------------------------------------------

    def _initial_status(self) -> str:
        if not self.config_data.can_read:
            return "Configuración no válida: revise el archivo .env."
        if not self.config_data.can_write:
            return "Modo solo lectura: falta la Write API Key."
        return "Listo."

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def show_config_errors(self) -> None:
        """Muestra un diálogo con los problemas de configuración, si los hay."""
        if not self.problems:
            return
        details = "\n\n".join(p.message for p in self.problems)
        messagebox.showwarning("Configuración incompleta", details, parent=self)


def run_app(config: ThingSpeakConfig, problems: Sequence[ConfigProblem] = ()) -> int:
    """Crea la ventana principal y arranca el bucle de eventos de Tkinter."""
    try:
        app = ReactorMonitorApp(config, problems)
    except tk.TclError as exc:
        print(f"[ERROR] No se pudo abrir la interfaz gráfica: {exc}", file=sys.stderr)
        return 1
    app.after(200, app.show_config_errors)
    app.mainloop()
    return 0
