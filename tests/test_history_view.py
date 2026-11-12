"""Pruebas de la vista de histórico (P4-03, issue #16).

Usan una función de consulta simulada: no se hacen peticiones a ThingSpeak.
Compatible con `pytest` y con `python -m unittest`.
"""

from __future__ import annotations

import time
import tkinter as tk
import unittest

from src.services.read_service import ReactorReading, ReadResult
from src.ui.history_view import EMPTY_VALUE, HistoryView, format_value, reading_to_row

CHANNEL_ID = "3566091"
READINGS = [
    ReactorReading(1, "2026-11-08T17:01:00Z", 52.4, 96.8, 35.2, 118.6, 42.3),
    ReactorReading(2, "2026-11-08T17:02:00Z", 58.7, 94.3, 41.9, 126.4, 46.8),
    ReactorReading(3, "2026-11-08T17:03:00Z", 63.9, None, 48.6, 162.8, 51.7),
]


def ok_result(records: list[ReactorReading], name: str | None = "Arc Reactor") -> ReadResult:
    return ReadResult(ok=True, channel_id=CHANNEL_ID, records=records, channel_name=name, status_code=200)


class FakeFetcher:
    """Simula `get_latest_readings` registrando cuántos registros se piden."""

    def __init__(self, *results: ReadResult | Exception) -> None:
        self.results = list(results)
        self.calls: list[int] = []

    def __call__(self, results: int) -> ReadResult:
        self.calls.append(results)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FormattingTests(unittest.TestCase):
    def test_format_value(self) -> None:
        self.assertEqual(format_value(52.4), "52.4")
        self.assertEqual(format_value(100.0), "100")
        self.assertEqual(format_value(None), EMPTY_VALUE)

    def test_reading_to_row_keeps_column_order(self) -> None:
        row = reading_to_row(READINGS[2])
        self.assertEqual(row, ("3", "2026-11-08 17:03:00 UTC", "63.9", EMPTY_VALUE, "48.6", "162.8", "51.7"))


class HistoryViewTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:  # entorno sin pantalla
            self.skipTest(f"Tkinter no disponible: {exc}")
        self.root.withdraw()
        self.statuses: list[str] = []

    def tearDown(self) -> None:
        self.root.destroy()

    def _view(self, fetch: FakeFetcher | None, **kwargs) -> HistoryView:
        view = HistoryView(self.root, fetch=fetch, on_status=self.statuses.append, **kwargs)
        view.pack()
        return view

    def _refresh_and_wait(self, view: HistoryView, timeout: float = 2.0) -> None:
        view.refresh()
        deadline = time.monotonic() + timeout
        while view._loading and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(view._loading, "La consulta no terminó a tiempo")

    def _rows(self, view: HistoryView) -> list[tuple[str, ...]]:
        return [tuple(view.tree.item(iid, "values")) for iid in view.tree.get_children()]

    def test_records_are_shown_newest_first(self) -> None:
        fetch = FakeFetcher(ok_result(READINGS))
        view = self._view(fetch)
        self._refresh_and_wait(view)
        rows = self._rows(view)
        self.assertEqual([row[0] for row in rows], ["3", "2", "1"])
        self.assertEqual(rows[2][2:], ("52.4", "96.8", "35.2", "118.6", "42.3"))
        self.assertEqual(rows[0][3], EMPTY_VALUE)
        self.assertIn("3 registros", view.message_var.get())
        self.assertIn("Última consulta", view.updated_var.get())
        self.assertFalse(view.refresh_button.instate(["disabled"]))

    def test_selected_number_of_records_is_requested(self) -> None:
        fetch = FakeFetcher(ok_result(READINGS))
        view = self._view(fetch)
        view.results_var.set("50")
        self._refresh_and_wait(view)
        self.assertEqual(fetch.calls, [50])

    def test_empty_channel_shows_specific_message(self) -> None:
        view = self._view(FakeFetcher(ok_result([])))
        self._refresh_and_wait(view)
        self.assertEqual(self._rows(view), [])
        self.assertIn("todavía no tiene registros", view.message_var.get())

    def test_error_keeps_previous_table_and_shows_message(self) -> None:
        error = ReadResult(ok=False, channel_id=CHANNEL_ID, status_code=404,
                           error_message="No se encontró el canal 3566091 en ThingSpeak (HTTP 404).")
        view = self._view(FakeFetcher(ok_result(READINGS), error))
        self._refresh_and_wait(view)
        self._refresh_and_wait(view)
        self.assertEqual(len(self._rows(view)), 3)
        self.assertIn("HTTP 404", view.message_var.get())
        self.assertIn("Consulta fallida", self.statuses[-1])

    def test_unexpected_exception_does_not_block_view(self) -> None:
        view = self._view(FakeFetcher(RuntimeError("fallo")))
        self._refresh_and_wait(view)
        self.assertIn("fallo", view.message_var.get())
        self.assertFalse(view.refresh_button.instate(["disabled"]))

    def test_disabled_view_does_not_query(self) -> None:
        fetch = FakeFetcher(ok_result(READINGS))
        view = self._view(fetch, disabled_reason="THINGSPEAK_CHANNEL_ID no es válido.")
        view.refresh()
        self.assertEqual(fetch.calls, [])
        self.assertTrue(view.refresh_button.instate(["disabled"]))
        self.assertIn("THINGSPEAK_CHANNEL_ID", view.message_var.get())


if __name__ == "__main__":
    unittest.main()
