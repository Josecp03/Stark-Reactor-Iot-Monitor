"""Vista de gráficas de evolución temporal del reactor Arc (P5-02, opcional).

Dibuja la evolución de cualquiera de las cinco variables del canal ThingSpeak
utilizando únicamente `tkinter.Canvas` de la librería estándar (sin dependencias
externas adicionales).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk

from src.services.read_service import FIELD_SPECS, FieldSpec, ReactorReading

FIELD_COLORS: dict[str, str] = {
    "field1": "#d9480f",
    "field2": "#1971c2",
    "field3": "#0ca678",
    "field4": "#7048e8",
    "field5": "#e67700",
}


def extract_field_series(
    records: Sequence[ReactorReading],
    field_key: str,
) -> list[tuple[int, float]]:
    """Extrae pares `(entry_id, valor)` ordenados por `entry_id` ascendente."""
    valid_keys = {spec.field_key for spec in FIELD_SPECS}
    if field_key not in valid_keys:
        raise ValueError(f"Campo desconocido: {field_key}")

    points: list[tuple[int, float]] = []
    for reading in sorted(records, key=lambda r: r.entry_id):
        value = getattr(reading, field_key, None)
        if value is not None:
            points.append((reading.entry_id, float(value)))
    return points


def summarize_series(points: Sequence[tuple[int, float]]) -> dict[str, float | int | None]:
    """Calcula estadísticas básicas (`count`, `latest`, `min`, `max`, `avg`) de la serie."""
    if not points:
        return {"count": 0, "latest": None, "min": None, "max": None, "avg": None}
    values = [v for _, v in points]
    return {
        "count": len(values),
        "latest": values[-1],
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
    }


class TelemetryChartsView(ttk.Frame):
    """Pestaña «Gráficas»: visualización de evolución de las variables del reactor."""

    def __init__(
        self,
        master: tk.Misc,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.on_refresh = on_refresh
        self._records: list[ReactorReading] = []

        self._spec_options: list[FieldSpec] = list(FIELD_SPECS)
        self.selected_label_var = tk.StringVar(
            value=self._format_option(self._spec_options[0])
        )
        self.stats_var = tk.StringVar()

        self._build()
        self._redraw()

    @staticmethod
    def _format_option(spec: FieldSpec) -> str:
        return f"{spec.label} ({spec.unit})"

    @property
    def selected_spec(self) -> FieldSpec:
        current = self.selected_label_var.get()
        for spec in self._spec_options:
            if self._format_option(spec) == current:
                return spec
        return self._spec_options[0]

    def _build(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(toolbar, text="Variable:").pack(side=tk.LEFT, padx=(0, 6))
        self.field_combo = ttk.Combobox(
            toolbar,
            textvariable=self.selected_label_var,
            values=[self._format_option(s) for s in self._spec_options],
            state="readonly",
            width=40,
        )
        self.field_combo.pack(side=tk.LEFT)
        self.field_combo.bind("<<ComboboxSelected>>", lambda _e: self._redraw())

        if self.on_refresh is not None:
            self.refresh_button = ttk.Button(
                toolbar, text="Actualizar datos", command=self.on_refresh
            )
            self.refresh_button.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(toolbar, textvariable=self.stats_var, foreground="#3c3c3c").pack(
            side=tk.RIGHT
        )

        self.canvas = tk.Canvas(
            self,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d0d7de",
            height=340,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

    def set_records(self, records: Sequence[ReactorReading]) -> None:
        """Actualiza los registros mostrados en la gráfica y redibuja."""
        self._records = list(records)
        self._redraw()

    def select_field(self, field_key: str) -> None:
        """Selecciona programáticamente el campo a graficar (`field1`..`field5`)."""
        for spec in self._spec_options:
            if spec.field_key == field_key:
                self.selected_label_var.set(self._format_option(spec))
                self._redraw()
                return
        raise ValueError(f"Campo desconocido: {field_key}")

    def _redraw(self) -> None:
        spec = self.selected_spec
        points = extract_field_series(self._records, spec.field_key)
        stats = summarize_series(points)

        if stats["count"] == 0:
            self.stats_var.set("Sin muestras disponibles")
        else:
            self.stats_var.set(
                f"Muestras: {stats['count']} · "
                f"Último: {stats['latest']:g} · "
                f"Mín: {stats['min']:g} · "
                f"Máx: {stats['max']:g} · "
                f"Media: {stats['avg']:.1f}"
            )

        self.canvas.delete("all")
        width = max(int(self.canvas.winfo_width()), 640)
        height = max(int(self.canvas.winfo_height()), 300)

        if not points:
            self.canvas.create_text(
                width // 2,
                height // 2,
                text="Sin datos para graficar. Pulse «Consultar / Actualizar» para cargar lecturas.",
                fill="#6b6b6b",
                font=("Segoe UI", 10),
            )
            return

        pad_left, pad_right, pad_top, pad_bottom = 64, 32, 36, 44
        plot_w = max(width - pad_left - pad_right, 100)
        plot_h = max(height - pad_top - pad_bottom, 80)

        values = [v for _, v in points]
        min_v, max_v = min(values), max(values)
        if min_v == max_v:
            span = max(abs(min_v) * 0.1, 1.0)
            y_min, y_max = min_v - span, max_v + span
        else:
            margin = (max_v - min_v) * 0.1
            y_min, y_max = min_v - margin, max_v + margin

        # Título de la gráfica
        self.canvas.create_text(
            pad_left,
            16,
            text=f"{spec.label} ({spec.unit})",
            anchor=tk.W,
            fill="#1f2328",
            font=("Segoe UI", 10, "bold"),
        )

        # Rejilla horizontal y etiquetas del eje Y
        steps = 4
        for idx in range(steps + 1):
            frac = idx / steps
            y = pad_top + plot_h * (1.0 - frac)
            val = y_min + (y_max - y_min) * frac
            self.canvas.create_line(
                pad_left, y, pad_left + plot_w, y, fill="#eaeef2"
            )
            self.canvas.create_text(
                pad_left - 8,
                y,
                text=f"{val:.1f}",
                anchor=tk.E,
                fill="#57606a",
                font=("Segoe UI", 8),
            )

        # Ejes X e Y
        self.canvas.create_line(
            pad_left,
            pad_top,
            pad_left,
            pad_top + plot_h,
            fill="#8c959f",
        )
        self.canvas.create_line(
            pad_left,
            pad_top + plot_h,
            pad_left + plot_w,
            pad_top + plot_h,
            fill="#8c959f",
        )

        # Coordenadas de cada punto
        n = len(points)
        coords: list[tuple[float, float, int, float]] = []
        for idx, (entry_id, val) in enumerate(points):
            x = pad_left + (plot_w / 2 if n == 1 else (idx / (n - 1)) * plot_w)
            y = pad_top + plot_h * (1.0 - (val - y_min) / (y_max - y_min))
            coords.append((x, y, entry_id, val))

        color = FIELD_COLORS.get(spec.field_key, "#1971c2")

        # Línea de evolución
        if len(coords) >= 2:
            flat_xy: list[float] = []
            for x, y, _, _ in coords:
                flat_xy.extend((x, y))
            self.canvas.create_line(*flat_xy, fill=color, width=2)

        # Puntos y etiquetas
        label_step = max(1, len(coords) // 10)
        for idx, (x, y, entry_id, val) in enumerate(coords):
            r = 4
            self.canvas.create_oval(
                x - r, y - r, x + r, y + r, fill=color, outline="#ffffff", width=1
            )
            if idx % label_step == 0 or idx == len(coords) - 1:
                self.canvas.create_text(
                    x,
                    y - 10,
                    text=f"{val:g}",
                    fill="#1f2328",
                    font=("Segoe UI", 8),
                )
                self.canvas.create_text(
                    x,
                    pad_top + plot_h + 14,
                    text=f"#{entry_id}",
                    fill="#57606a",
                    font=("Segoe UI", 8),
                )
