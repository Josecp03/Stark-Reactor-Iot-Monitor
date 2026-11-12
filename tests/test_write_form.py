"""Pruebas del formulario de entrada manual (P4-02, issue #15).

Usan un servicio de escritura simulado: no se hacen peticiones a ThingSpeak.
Compatible con `pytest` y con `python -m unittest`.
"""

from __future__ import annotations

import time
import tkinter as tk
import unittest
from dataclasses import dataclass
from pathlib import Path

from src.ui.write_form import FORM_FIELDS, ManualEntryForm, load_test_samples, parse_field_value

VALID_SAMPLE = {"field1": "52.4", "field2": "96.8", "field3": "35.2", "field4": "118.6", "field5": "42.3"}


@dataclass
class FakeResult:
    success: bool
    entry_id: int | None = None
    error_message: str | None = None
    cooldown_remaining: float = 0.0


class FakeWriter:
    """Simula `ThingSpeakWriter` registrando las llamadas recibidas."""

    def __init__(self, result: FakeResult | None = None, cooldown: float = 0.0) -> None:
        self.result = result or FakeResult(success=True, entry_id=7)
        self.cooldown = cooldown
        self.calls: list[tuple[float, ...]] = []

    def send_sample(self, *args: float) -> FakeResult:
        self.calls.append(args)
        return self.result

    def get_cooldown_remaining(self) -> float:
        return self.cooldown


class ParseFieldValueTests(unittest.TestCase):
    def test_accepts_dot_and_comma_decimals(self) -> None:
        spec = FORM_FIELDS[0]
        self.assertEqual(parse_field_value("52.4", spec), (52.4, None))
        self.assertEqual(parse_field_value(" 52,4 ", spec), (52.4, None))

    def test_rejects_empty_and_non_numeric(self) -> None:
        spec = FORM_FIELDS[0]
        self.assertIsNotNone(parse_field_value("", spec)[1])
        self.assertIsNotNone(parse_field_value("abc", spec)[1])
        self.assertIsNotNone(parse_field_value("nan", spec)[1])

    def test_range_only_for_stability_and_coolant(self) -> None:
        by_key = {spec.field_key: spec for spec in FORM_FIELDS}
        self.assertIsNotNone(parse_field_value("100.1", by_key["field2"])[1])
        self.assertIsNotNone(parse_field_value("-1", by_key["field3"])[1])
        self.assertIsNone(parse_field_value("0", by_key["field2"])[1])
        self.assertIsNone(parse_field_value("100", by_key["field3"])[1])
        # Sin rango definido en el enunciado: no se limita
        self.assertIsNone(parse_field_value("4500", by_key["field5"])[1])
        self.assertIsNone(parse_field_value("120", by_key["field1"])[1])


class LoadTestSamplesTests(unittest.TestCase):
    def test_loads_the_ten_teacher_samples(self) -> None:
        samples = load_test_samples()
        self.assertEqual(len(samples), 10)
        self.assertEqual(samples[0]["field1"], "52.4")

    def test_missing_csv_returns_empty_list(self) -> None:
        self.assertEqual(load_test_samples(Path("no-existe.csv")), [])


class ManualEntryFormTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:  # entorno sin pantalla
            self.skipTest(f"Tkinter no disponible: {exc}")
        self.root.withdraw()
        self.sent: list[int | None] = []

    def tearDown(self) -> None:
        self.root.destroy()

    def _form(self, writer: FakeWriter | None, **kwargs) -> ManualEntryForm:
        form = ManualEntryForm(self.root, writer=writer, on_sent=self.sent.append, samples=[], **kwargs)
        form.pack()
        return form

    def _fill(self, form: ManualEntryForm, values: dict[str, str]) -> None:
        for key, value in values.items():
            form.vars[key].set(value)

    def _wait_until_idle(self, form: ManualEntryForm, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while form._sending and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(form._sending, "El envío no terminó a tiempo")

    def test_valid_sample_is_sent_with_numeric_values(self) -> None:
        writer = FakeWriter()
        form = self._form(writer)
        self._fill(form, {**VALID_SAMPLE, "field1": "52,4"})
        form.submit()
        self._wait_until_idle(form)
        self.assertEqual(writer.calls, [(52.4, 96.8, 35.2, 118.6, 42.3)])
        self.assertIn("registro n.º 7", form.message_var.get())
        self.assertEqual(self.sent, [7])
        self.assertTrue(all(var.get() == "" for var in form.vars.values()))

    def test_invalid_field_is_marked_and_nothing_is_sent(self) -> None:
        writer = FakeWriter()
        form = self._form(writer)
        self._fill(form, {**VALID_SAMPLE, "field2": "150"})
        form.submit()
        self.assertEqual(writer.calls, [])
        self.assertIn("entre 0 y 100", form.error_labels["field2"].cget("text"))
        self.assertEqual(form.error_labels["field1"].cget("text"), "")

    def test_field_error_disappears_when_user_edits(self) -> None:
        form = self._form(FakeWriter())
        form.submit()
        self.assertNotEqual(form.error_labels["field1"].cget("text"), "")
        form.vars["field1"].set("5")
        self.assertEqual(form.error_labels["field1"].cget("text"), "")

    def test_service_error_is_shown_and_values_are_kept(self) -> None:
        writer = FakeWriter(FakeResult(success=False, error_message="ThingSpeak rechazó la escritura (respuesta 0)."))
        form = self._form(writer)
        self._fill(form, VALID_SAMPLE)
        form.submit()
        self._wait_until_idle(form)
        self.assertIn("respuesta 0", form.message_var.get())
        self.assertEqual(form.vars["field1"].get(), "52.4")
        self.assertEqual(self.sent, [])

    def test_cooldown_disables_send_button_with_countdown(self) -> None:
        writer = FakeWriter(cooldown=12.3)
        form = self._form(writer)
        self.assertTrue(form.send_button.instate(["disabled"]))
        self.assertIn("13 s", form.send_button.cget("text"))
        self._fill(form, VALID_SAMPLE)
        form.submit()
        self.assertEqual(writer.calls, [])

        writer.cooldown = 0.0
        form._refresh_send_button()
        self.assertFalse(form.send_button.instate(["disabled"]))
        self.assertEqual(form.send_button.cget("text"), "Enviar")

    def test_without_writer_form_is_disabled_with_reason(self) -> None:
        form = self._form(None, disabled_reason="Falta THINGSPEAK_WRITE_API_KEY.")
        self.assertTrue(form.send_button.instate(["disabled"]))
        self.assertTrue(form.entries["field1"].instate(["disabled"]))
        self.assertIn("THINGSPEAK_WRITE_API_KEY", form.message_var.get())

    def test_fill_sample_only_fills_fields(self) -> None:
        writer = FakeWriter()
        form = self._form(writer)
        form.fill_sample(VALID_SAMPLE)
        self.assertEqual(form.vars["field4"].get(), "118.6")
        self.assertEqual(writer.calls, [])


if __name__ == "__main__":
    unittest.main()
