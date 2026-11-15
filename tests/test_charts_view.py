"""Pruebas de la vista de gráficas de evolución (P5-02)."""

from __future__ import annotations

import tkinter as tk
import unittest

from src.services.read_service import ReactorReading
from src.ui.charts_view import TelemetryChartsView, extract_field_series, summarize_series

SAMPLE_READINGS = [
    ReactorReading(1, "2026-11-08T17:01:00Z", 52.4, 96.8, 35.2, 118.6, 42.3),
    ReactorReading(2, "2026-11-08T17:02:00Z", 58.7, None, 41.9, 126.4, 46.8),
    ReactorReading(3, "2026-11-08T17:03:00Z", 63.9, 91.5, 48.6, 162.8, 51.7),
]


class ChartSeriesTests(unittest.TestCase):
    def test_extract_field_series_skips_none_and_sorts_by_entry_id(self) -> None:
        reversed_readings = list(reversed(SAMPLE_READINGS))
        series_f1 = extract_field_series(reversed_readings, "field1")
        self.assertEqual(series_f1, [(1, 52.4), (2, 58.7), (3, 63.9)])

        series_f2 = extract_field_series(reversed_readings, "field2")
        self.assertEqual(series_f2, [(1, 96.8), (3, 91.5)])

    def test_summarize_series_computes_stats(self) -> None:
        empty_stats = summarize_series([])
        self.assertEqual(empty_stats["count"], 0)
        self.assertIsNone(empty_stats["latest"])

        stats = summarize_series([(1, 50.0), (2, 60.0), (3, 70.0)])
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["latest"], 70.0)
        self.assertEqual(stats["min"], 50.0)
        self.assertEqual(stats["max"], 70.0)
        self.assertEqual(stats["avg"], 60.0)


class TelemetryChartsViewTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tkinter no disponible: {exc}")
        self.root.withdraw()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_renders_empty_and_populated_series(self) -> None:
        view = TelemetryChartsView(self.root)
        view.pack()
        self.assertIn("Sin muestras", view.stats_var.get())

        view.set_records(SAMPLE_READINGS)
        self.assertIn("Muestras: 3", view.stats_var.get())
        self.assertGreater(len(view.canvas.find_all()), 0)

        view.select_field("field2")
        self.assertIn("Muestras: 2", view.stats_var.get())


if __name__ == "__main__":
    unittest.main()
