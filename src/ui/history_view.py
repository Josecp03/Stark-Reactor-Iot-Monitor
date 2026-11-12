"""Vista de consulta e histórico del canal ThingSpeak (P4-03, issue #16).

Muestra en una tabla los últimos registros del canal obtenidos con el servicio
de lectura (`get_latest_readings`), con su número de registro, fecha y los
cinco valores del reactor con sus unidades.

- Botón «Consultar / Actualizar» y selector del número de registros.
- Consulta en segundo plano para no bloquear la ventana.
- Mensajes diferenciados para: consultando, canal sin registros y error de
  comunicación.
- Registros más recientes primero.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import ttk
from typing import Any

from src.services.read_service import FIELD_SPECS, ReactorReading, ReadResult

RESULT_POLL_MS = 100
RESULTS_OPTIONS: tuple[int, ...] = (10, 25, 50, 100)
DEFAULT_RESULTS = 10
EMPTY_VALUE = "—"

COLOR_OK = "#1e7b34"
COLOR_ERROR = "#b3261e"
COLOR_INFO = "#3c3c3c"

# Cabeceras cortas para la tabla; el nombre completo de cada campo está en FIELD_SPECS.
SHORT_HEADINGS: dict[str, str] = {
    "field1": "Carga núcleo",
    "field2": "Estabilidad",
    "field3": "Refrigerante",
    "field4": "Latencia JARVIS",
    "field5": "Repulsores",
}

COLUMNS: tuple[str, ...] = ("entry_id", "created_at") + tuple(spec.field_key for spec in FIELD_SPECS)

Fetcher = Callable[[int], ReadResult]


def format_value(value: float | None) -> str:
    """Formatea un valor numérico para la tabla; `None` se muestra como «—»."""
    if value is None:
        return EMPTY_VALUE
    return f"{value:g}"


def reading_to_row(reading: ReactorReading) -> tuple[str, ...]:
    """Convierte un registro en la fila de la tabla (mismo orden que `COLUMNS`)."""
    return (
        str(reading.entry_id),
        reading.formatted_timestamp or EMPTY_VALUE,
        *(format_value(getattr(reading, spec.field_key)) for spec in FIELD_SPECS),
    )


class HistoryView(ttk.Frame):
    """Pestaña «Histórico»: consulta y tabla de los últimos registros del canal."""

    def __init__(
        self,
        master: tk.Misc,
        fetch: Fetcher | None,
        disabled_reason: str | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        if fetch is None and not disabled_reason:
            disabled_reason = "El servicio de lectura no está disponible."
        self.fetch = fetch
        self.disabled_reason = disabled_reason
        self.on_status = on_status

        self.results_var = tk.StringVar(value=str(DEFAULT_RESULTS))
        self.message_var = tk.StringVar()
        self.updated_var = tk.StringVar()

        self._results: queue.Queue[Any] = queue.Queue()
        self._loading = False

        self._build()
        if self.disabled_reason:
            self.refresh_button.state(["disabled"])
            self.results_combo.state(["disabled"])
            self.show_message(self.disabled_reason, COLOR_ERROR)
        else:
            self.show_message("Pulse «Consultar / Actualizar» para ver los últimos registros del canal.")

    # --- Construcción ----------------------------------------------------------------

    def _build(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        self.refresh_button = ttk.Button(
            toolbar, text="Consultar / Actualizar", command=self.refresh, width=24
        )
        self.refresh_button.pack(side=tk.LEFT)

        ttk.Label(toolbar, text="Registros:").pack(side=tk.LEFT, padx=(16, 4))
        self.results_combo = ttk.Combobox(
            toolbar,
            textvariable=self.results_var,
            values=[str(n) for n in RESULTS_OPTIONS],
            state="readonly",
            width=5,
        )
        self.results_combo.pack(side=tk.LEFT)

        ttk.Label(toolbar, textvariable=self.updated_var, foreground="#6b6b6b").pack(side=tk.RIGHT)

        self.message_label = tk.Label(
            self, textvariable=self.message_var, anchor=tk.W, justify=tk.LEFT, wraplength=880
        )
        self.message_label.pack(fill=tk.X, pady=(0, 8))

        table = ttk.Frame(self)
        table.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table, columns=COLUMNS, show="headings", selectmode="browse", height=12)
        self.tree.heading("entry_id", text="N.º")
        self.tree.column("entry_id", width=55, minwidth=45, anchor=tk.E, stretch=False)
        self.tree.heading("created_at", text="Fecha (UTC)")
        self.tree.column("created_at", width=165, minwidth=140, anchor=tk.W, stretch=False)
        for spec in FIELD_SPECS:
            self.tree.heading(spec.field_key, text=f"{SHORT_HEADINGS[spec.field_key]} ({spec.unit})")
            self.tree.column(spec.field_key, width=120, minwidth=90, anchor=tk.E)

        scrollbar = ttk.Scrollbar(table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        legend = " · ".join(f"{SHORT_HEADINGS[s.field_key]}: {s.label}" for s in FIELD_SPECS)
        ttk.Label(self, text=legend, foreground="#6b6b6b", wraplength=880, justify=tk.LEFT).pack(
            fill=tk.X, pady=(8, 0)
        )

    # --- Consulta --------------------------------------------------------------------

    @property
    def selected_results(self) -> int:
        try:
            value = int(self.results_var.get())
        except ValueError:
            return DEFAULT_RESULTS
        return value if value > 0 else DEFAULT_RESULTS

    def refresh(self) -> None:
        """Consulta los últimos registros en segundo plano y actualiza la tabla."""
        if self.fetch is None or self.disabled_reason or self._loading:
            return
        self._loading = True
        self.refresh_button.state(["disabled"])
        self.refresh_button.configure(text="Consultando…")
        self.show_message("Consultando ThingSpeak…")
        self._notify_status("Consultando registros en ThingSpeak…")

        threading.Thread(
            target=self._fetch_in_background, args=(self.selected_results,), daemon=True
        ).start()
        self.after(RESULT_POLL_MS, self._poll_result)

    def _fetch_in_background(self, results: int) -> None:
        try:
            result = self.fetch(results)  # type: ignore[misc]
        except Exception as exc:  # el servicio no debería lanzar, pero no se bloquea la UI
            result = exc
        self._results.put(result)

    def _poll_result(self) -> None:
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            self.after(RESULT_POLL_MS, self._poll_result)
            return
        self._loading = False
        self.refresh_button.configure(text="Consultar / Actualizar")
        self.refresh_button.state(["!disabled"])
        self.show_result(result)

    def show_result(self, result: ReadResult | Exception) -> None:
        """Presenta en la tabla y en el mensaje el resultado de una consulta."""
        if isinstance(result, Exception):
            message = f"Error inesperado al consultar ThingSpeak: {result}"
            self.show_message(message, COLOR_ERROR)
            self._notify_status(message)
            return

        if not result.ok:
            message = result.error_message or "No se pudo consultar el canal."
            # Se conservan los registros de la consulta anterior, si los hay.
            self.show_message(f"{message} Se mantiene la última tabla consultada.", COLOR_ERROR)
            self._notify_status(f"Consulta fallida: {message}")
            return

        self._fill_table(result.records)
        self.updated_var.set(f"Última consulta: {datetime.now():%H:%M:%S}")
        channel = f"«{result.channel_name}»" if result.channel_name else f"el canal {result.channel_id}"
        if result.is_empty:
            message = f"Consulta correcta: {channel} todavía no tiene registros."
            self.show_message(message, COLOR_INFO)
        else:
            count = len(result.records)
            noun = "registro" if count == 1 else "registros"
            message = f"{count} {noun} de {channel}, del más reciente al más antiguo."
            self.show_message(message, COLOR_OK)
        self._notify_status(message)

    def _fill_table(self, records: list[ReactorReading]) -> None:
        self.tree.delete(*self.tree.get_children())
        for reading in sorted(records, key=lambda r: r.entry_id, reverse=True):
            self.tree.insert("", tk.END, iid=str(reading.entry_id), values=reading_to_row(reading))

    # --- Mensajes --------------------------------------------------------------------

    def show_message(self, text: str, color: str = COLOR_INFO) -> None:
        self.message_var.set(text)
        self.message_label.configure(fg=color)

    def _notify_status(self, text: str) -> None:
        if self.on_status is not None:
            self.on_status(text)
