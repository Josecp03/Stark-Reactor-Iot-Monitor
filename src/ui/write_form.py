"""Formulario de entrada manual de muestras del reactor (P4-02, issue #15).

Permite escribir a mano los cinco valores del reactor y enviarlos a ThingSpeak
mediante el servicio de escritura (`ThingSpeakWriter.send_sample`).

- Cinco campos etiquetados con su unidad o rango.
- Validación inmediata de cada campo antes de enviar (campo marcado en rojo).
- Envío en segundo plano para no bloquear la ventana.
- Botón `Enviar` desactivado mientras hay un envío en curso y durante el
  intervalo mínimo entre escrituras, con cuenta atrás visible.
- Opción de rellenar el formulario con una de las muestras de prueba del CSV;
  el envío sigue siendo manual.
"""

from __future__ import annotations

import csv
import math
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from typing import Any, Protocol

from src.config import PROJECT_ROOT

SAMPLES_CSV_PATH = PROJECT_ROOT / "data" / "reactor_samples.csv"

# Intervalo de refresco de la cuenta atrás y de la cola de resultados (ms)
COUNTDOWN_REFRESH_MS = 250
RESULT_POLL_MS = 100

COLOR_OK = "#1e7b34"
COLOR_ERROR = "#b3261e"
COLOR_INFO = "#3c3c3c"


@dataclass(frozen=True)
class FormField:
    """Campo del formulario manual."""

    field_key: str
    label: str
    unit: str
    hint: str
    min_value: float | None = None
    max_value: float | None = None


# Rangos solo donde el enunciado los define (estabilidad y refrigerante: 0–100).
FORM_FIELDS: tuple[FormField, ...] = (
    FormField("field1", "Carga de energía del núcleo", "%", "Ej.: 52.4"),
    FormField("field2", "Estabilidad del campo", "0–100", "Entre 0 y 100", 0.0, 100.0),
    FormField("field3", "Flujo de refrigerante de vibranium", "0–100", "Entre 0 y 100", 0.0, 100.0),
    FormField("field4", "Latencia del protocolo JARVIS", "ms", "Ej.: 118.6"),
    FormField("field5", "Consumo energético de los repulsores", "W", "Ej.: 42.3"),
)


class SampleWriter(Protocol):
    """Interfaz mínima del servicio de escritura que usa el formulario."""

    def send_sample(
        self,
        core_load: Any,
        field_stability: Any,
        coolant_flow: Any,
        jarvis_latency: Any,
        repulsor_power: Any,
    ) -> Any: ...

    def get_cooldown_remaining(self) -> float: ...


def parse_field_value(raw: str, spec: FormField) -> tuple[float | None, str | None]:
    """Valida el texto de un campo. Devuelve `(valor, None)` o `(None, mensaje de error)`.

    Acepta coma o punto como separador decimal.
    """
    text = raw.strip().replace(",", ".")
    if not text:
        return None, f"«{spec.label}» es obligatorio."
    try:
        value = float(text)
    except ValueError:
        return None, f"«{spec.label}» debe ser un número (por ejemplo 52.4)."
    if not math.isfinite(value):
        return None, f"«{spec.label}» debe ser un número válido."
    if spec.min_value is not None and value < spec.min_value:
        return None, f"«{spec.label}» debe estar entre {spec.min_value:g} y {spec.max_value:g}."
    if spec.max_value is not None and value > spec.max_value:
        return None, f"«{spec.label}» debe estar entre {spec.min_value:g} y {spec.max_value:g}."
    return value, None


def load_test_samples(path: Path = SAMPLES_CSV_PATH) -> list[dict[str, str]]:
    """Lee las muestras de prueba del profesorado. Devuelve una lista vacía si no existe el CSV."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = [spec.field_key for spec in FORM_FIELDS]
    return [row for row in rows if all((row.get(k) or "").strip() for k in keys)]


class ManualEntryForm(ttk.Frame):
    """Pestaña «Enviar muestra»: entrada manual de las cinco variables del reactor."""

    def __init__(
        self,
        master: tk.Misc,
        writer: SampleWriter | None,
        disabled_reason: str | None = None,
        on_sent: Callable[[int | None], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        samples: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(master)
        self.writer = writer
        if writer is None and not disabled_reason:
            disabled_reason = "El servicio de escritura no está disponible."
        self.disabled_reason = disabled_reason
        self.on_sent = on_sent
        self.on_status = on_status
        self.samples = load_test_samples() if samples is None else samples

        self.vars: dict[str, tk.StringVar] = {}
        self.entries: dict[str, ttk.Entry] = {}
        self.error_labels: dict[str, ttk.Label] = {}
        self.message_var = tk.StringVar()
        self.sample_var = tk.StringVar()

        self._results: queue.Queue[Any] = queue.Queue()
        self._sending = False
        self._countdown_job: str | None = None

        self._configure_styles()
        self._build()
        self._refresh_send_button()

    # --- Construcción ----------------------------------------------------------------

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("Invalid.TEntry", fieldbackground="#fde7e6")
        style.configure("FieldError.TLabel", foreground=COLOR_ERROR)
        style.configure("Hint.TLabel", foreground="#6b6b6b")

    def _build(self) -> None:
        ttk.Label(
            self,
            text="Introduzca los cinco valores del reactor y pulse «Enviar». "
            "Se admite coma o punto decimal.",
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 12))

        for row, spec in enumerate(FORM_FIELDS, start=1):
            ttk.Label(self, text=f"{spec.label} ({spec.unit})").grid(
                row=row, column=0, sticky=tk.W, padx=(0, 12), pady=4
            )
            var = tk.StringVar()
            entry = ttk.Entry(self, textvariable=var, width=14, justify=tk.RIGHT)
            entry.grid(row=row, column=1, sticky=tk.W, pady=4)
            entry.bind("<Return>", lambda _event: self.submit())
            var.trace_add("write", lambda *_args, key=spec.field_key: self._clear_field_error(key))
            ttk.Label(self, text=spec.hint, style="Hint.TLabel").grid(
                row=row, column=2, sticky=tk.W, padx=(8, 12)
            )
            error_label = ttk.Label(self, text="", style="FieldError.TLabel")
            error_label.grid(row=row, column=3, sticky=tk.W)

            self.vars[spec.field_key] = var
            self.entries[spec.field_key] = entry
            self.error_labels[spec.field_key] = error_label

        buttons = ttk.Frame(self)
        buttons.grid(row=len(FORM_FIELDS) + 1, column=0, columnspan=4, sticky=tk.W, pady=(16, 8))
        self.send_button = ttk.Button(buttons, text="Enviar", command=self.submit, width=22)
        self.send_button.pack(side=tk.LEFT)
        self.clear_button = ttk.Button(buttons, text="Limpiar", command=self.clear)
        self.clear_button.pack(side=tk.LEFT, padx=(8, 0))

        self.message_label = tk.Label(
            self, textvariable=self.message_var, anchor=tk.W, justify=tk.LEFT, wraplength=820
        )
        self.message_label.grid(row=len(FORM_FIELDS) + 2, column=0, columnspan=4, sticky=tk.W)

        if self.samples:
            self._build_sample_picker(row=len(FORM_FIELDS) + 3)

        self.columnconfigure(3, weight=1)

        if self.disabled_reason:
            for entry in self.entries.values():
                entry.state(["disabled"])
            self.show_message(self.disabled_reason, COLOR_ERROR)

    def _build_sample_picker(self, row: int) -> None:
        box = ttk.LabelFrame(self, text="Muestras de prueba (opcional)", padding=(10, 6))
        box.grid(row=row, column=0, columnspan=4, sticky=tk.EW, pady=(20, 0))
        ttk.Label(
            box,
            text="Rellena el formulario con una muestra del enunciado. Después revise y pulse «Enviar».",
        ).pack(anchor=tk.W)
        line = ttk.Frame(box)
        line.pack(anchor=tk.W, pady=(6, 0))
        options = [
            f"Muestra {i}: " + " · ".join(sample[spec.field_key] for spec in FORM_FIELDS)
            for i, sample in enumerate(self.samples, start=1)
        ]
        self.sample_combo = ttk.Combobox(
            line, textvariable=self.sample_var, values=options, state="readonly", width=48
        )
        self.sample_combo.pack(side=tk.LEFT)
        self.fill_button = ttk.Button(line, text="Rellenar", command=self.fill_selected_sample)
        self.fill_button.pack(side=tk.LEFT, padx=(8, 0))
        if self.disabled_reason:
            self.sample_combo.state(["disabled"])
            self.fill_button.state(["disabled"])

    # --- Acciones --------------------------------------------------------------------

    def fill_selected_sample(self) -> None:
        index = self.sample_combo.current()
        if index < 0:
            self.show_message("Seleccione primero una muestra de la lista.", COLOR_INFO)
            return
        self.fill_sample(self.samples[index])
        self.show_message(f"Muestra {index + 1} cargada. Revise los valores y pulse «Enviar».", COLOR_INFO)

    def fill_sample(self, sample: dict[str, str]) -> None:
        for spec in FORM_FIELDS:
            self.vars[spec.field_key].set(sample.get(spec.field_key, "").strip())

    def clear(self) -> None:
        for var in self.vars.values():
            var.set("")
        self.message_var.set("")
        self.entries[FORM_FIELDS[0].field_key].focus_set()

    def validate(self) -> dict[str, float] | None:
        """Valida todos los campos, marca los erróneos y devuelve los valores o `None`."""
        values: dict[str, float] = {}
        first_invalid: str | None = None
        for spec in FORM_FIELDS:
            value, error = parse_field_value(self.vars[spec.field_key].get(), spec)
            if error:
                self._set_field_error(spec.field_key, error)
                first_invalid = first_invalid or spec.field_key
            else:
                values[spec.field_key] = value  # type: ignore[assignment]
        if first_invalid:
            self.entries[first_invalid].focus_set()
            self.show_message("Revise los campos con error y vuelva a pulsar «Enviar».", COLOR_ERROR)
            return None
        return values

    def submit(self) -> None:
        """Valida el formulario y envía la muestra en segundo plano."""
        if self.writer is None or self.disabled_reason or self._sending:
            return
        remaining = self.writer.get_cooldown_remaining()
        if remaining > 0:
            self.show_message(f"Espere {math.ceil(remaining)} s antes de enviar otra muestra.", COLOR_INFO)
            self._refresh_send_button()
            return

        values = self.validate()
        if values is None:
            return

        self._sending = True
        self._refresh_send_button()
        self.show_message("Enviando muestra a ThingSpeak…", COLOR_INFO)
        self._notify_status("Enviando muestra a ThingSpeak…")

        args = [values[spec.field_key] for spec in FORM_FIELDS]
        threading.Thread(target=self._send_in_background, args=(args,), daemon=True).start()
        self.after(RESULT_POLL_MS, self._poll_result)

    def _send_in_background(self, args: list[float]) -> None:
        try:
            result = self.writer.send_sample(*args)  # type: ignore[union-attr]
        except Exception as exc:  # el servicio no debería lanzar, pero no se bloquea la UI
            result = exc
        self._results.put(result)

    def _poll_result(self) -> None:
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            self.after(RESULT_POLL_MS, self._poll_result)
            return
        self._sending = False
        self._handle_result(result)
        self._refresh_send_button()

    def _handle_result(self, result: Any) -> None:
        if isinstance(result, Exception):
            message = f"Error inesperado al enviar la muestra: {result}"
            self.show_message(message, COLOR_ERROR)
            self._notify_status(message)
            return

        if getattr(result, "success", False):
            entry_id = getattr(result, "entry_id", None)
            message = f"Muestra guardada en ThingSpeak (registro n.º {entry_id})."
            self.show_message(message, COLOR_OK)
            self._notify_status(message)
            for var in self.vars.values():
                var.set("")
            if self.on_sent is not None:
                self.on_sent(entry_id)
            return

        error = getattr(result, "error_message", None) or "No se pudo enviar la muestra."
        self.show_message(error, COLOR_ERROR)
        self._notify_status(f"Envío fallido: {error}")

    # --- Estado del botón y cuenta atrás ---------------------------------------------

    def _refresh_send_button(self) -> None:
        if self._countdown_job is not None:
            self.after_cancel(self._countdown_job)
            self._countdown_job = None

        if self.writer is None or self.disabled_reason:
            self.send_button.configure(text="Enviar (no disponible)")
            self.send_button.state(["disabled"])
            return
        if self._sending:
            self.send_button.configure(text="Enviando…")
            self.send_button.state(["disabled"])
            return

        remaining = self.writer.get_cooldown_remaining()
        if remaining > 0:
            self.send_button.configure(text=f"Enviar (espere {math.ceil(remaining)} s)")
            self.send_button.state(["disabled"])
            self._countdown_job = self.after(COUNTDOWN_REFRESH_MS, self._refresh_send_button)
            return

        self.send_button.configure(text="Enviar")
        self.send_button.state(["!disabled"])

    # --- Mensajes --------------------------------------------------------------------

    def show_message(self, text: str, color: str = COLOR_INFO) -> None:
        self.message_var.set(text)
        self.message_label.configure(fg=color)

    def _notify_status(self, text: str) -> None:
        if self.on_status is not None:
            self.on_status(text)

    def _set_field_error(self, key: str, message: str) -> None:
        self.entries[key].configure(style="Invalid.TEntry")
        self.error_labels[key].configure(text=message)

    def _clear_field_error(self, key: str) -> None:
        self.entries[key].configure(style="TEntry")
        self.error_labels[key].configure(text="")
