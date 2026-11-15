"""Pruebas de extremo a extremo (E2E) de Stark Reactor IoT Monitor."""

from __future__ import annotations

import gc
import json
import socket
import threading
import time
import tkinter as tk
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests

from src.config import DEFAULT_CHANNEL_ID, ThingSpeakConfig
from src.services.read_service import get_latest_readings
from src.ui.app import ReactorMonitorApp
from src.ui.write_form import FORM_FIELDS, load_test_samples


class _ThingSpeakState:
    def __init__(self, channel_id: str = DEFAULT_CHANNEL_ID, write_key: str = "E2E_WRITE_KEY") -> None:
        self.channel_id = channel_id
        self.write_key = write_key
        self.feeds: list[dict[str, Any]] = []
        self.update_calls: int = 0
        self.force_zero: bool = False
        self.force_status: int | None = None
        self.lock = threading.Lock()

    def handle_get(self, path: str, params: dict[str, str]) -> tuple[int, str, bytes]:
        with self.lock:
            if self.force_status is not None:
                return (
                    self.force_status,
                    "application/json; charset=utf-8",
                    b'{"error":"server error"}',
                )

            if path == "/update":
                self.update_calls += 1
                if params.get("api_key") != self.write_key or self.force_zero:
                    return 200, "text/plain; charset=utf-8", b"0"

                entry_id = len(self.feeds) + 1
                entry = {
                    "created_at": f"2026-11-15T12:00:{entry_id:02d}Z",
                    "entry_id": entry_id,
                    "field1": params.get("field1"),
                    "field2": params.get("field2"),
                    "field3": params.get("field3"),
                    "field4": params.get("field4"),
                    "field5": params.get("field5"),
                }
                self.feeds.append(entry)
                return 200, "text/plain; charset=utf-8", str(entry_id).encode("utf-8")

            expected_feeds_path = f"/channels/{self.channel_id}/feeds.json"
            if path == expected_feeds_path:
                limit = int(params.get("results", "10"))
                payload = {
                    "channel": {
                        "id": int(self.channel_id),
                        "name": "Stark Industries - Arc Reactor Monitoring",
                    },
                    "feeds": self.feeds[-limit:],
                }
                return (
                    200,
                    "application/json; charset=utf-8",
                    json.dumps(payload).encode("utf-8"),
                )

        return 404, "text/plain; charset=utf-8", b"Not Found"


def _make_handler(state: _ThingSpeakState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            status, content_type, data = state.handle_get(parsed.path, params)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    return Handler


def _loopback_available(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


class EndToEndAppFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = _ThingSpeakState()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self.state))
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        self._patcher = None
        if not _loopback_available(host, port):
            self._patcher = patch("requests.get", side_effect=self._in_process_get)
            self._patcher.start()

        self.config = ThingSpeakConfig(
            channel_id=self.state.channel_id,
            write_api_key=self.state.write_key,
            base_url=self.base_url,
            timeout=5.0,
        )
        try:
            self.app = ReactorMonitorApp(self.config)
        except tk.TclError as exc:
            self._cleanup_server()
            self.skipTest(f"Tkinter no disponible: {exc}")
        self.app.withdraw()

    def tearDown(self) -> None:
        if hasattr(self, "app"):
            if self.app.write_form._countdown_job is not None:
                self.app.write_form.after_cancel(self.app.write_form._countdown_job)
                self.app.write_form._countdown_job = None
            self.app.update_idletasks()
            self.app.destroy()
            del self.app
            gc.collect()
        self._cleanup_server()

    def _cleanup_server(self) -> None:
        if self._patcher is not None:
            self._patcher.stop()
            self._patcher = None
        self.server.shutdown()
        self.server.server_close()

    def _in_process_get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        parsed = urlparse(url)
        merged_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if params:
            for key, value in params.items():
                if value is not None:
                    merged_params[str(key)] = str(value)
        status, content_type, data = self.state.handle_get(parsed.path, merged_params)
        response = requests.Response()
        response.status_code = status
        response.headers["Content-Type"] = content_type
        response._content = data
        response.encoding = "utf-8"
        response.url = url
        return response

    def _wait_for_ui_idle(self, timeout: float = 3.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.update()
            if not self.app.write_form._sending and not self.app.history_view._loading:
                return
            time.sleep(0.01)
        self.fail("La operación en segundo plano de la interfaz no terminó a tiempo.")

    def test_manual_write_and_history_consultation(self) -> None:
        form = self.app.write_form
        history = self.app.history_view

        samples = load_test_samples()
        self.assertEqual(len(samples), 10)
        form.fill_sample(samples[0])
        form.submit()
        self._wait_for_ui_idle()

        self.assertIn("registro n.º 1", form.message_var.get())
        self.assertEqual(self.state.update_calls, 1)

        if len(history.tree.get_children()) != 1:
            history.refresh()
            self._wait_for_ui_idle()

        rows = [tuple(history.tree.item(iid, "values")) for iid in history.tree.get_children()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "1")
        self.assertEqual(rows[0][2:], ("52.4", "96.8", "35.2", "118.6", "42.3"))

        if hasattr(history, "diagnostic_level"):
            self.assertEqual(history.diagnostic_level, "NOMINAL")
        if hasattr(self.app, "charts_view"):
            self.assertIn("Muestras: 1", self.app.charts_view.stats_var.get())

        # Un segundo envío inmediato debe bloquearse por el intervalo de 15 s sin llegar al servidor
        form.fill_sample(samples[1])
        form.submit()
        self.assertEqual(self.state.update_calls, 1)
        self.assertTrue(form.send_button.instate(["disabled"]))

    def test_all_ten_csv_samples_roundtrip(self) -> None:
        assert self.app.write_form.writer is not None
        self.app.write_form.writer.cooldown_sec = 0.0  # type: ignore[attr-defined]

        samples = load_test_samples()
        for sample in samples:
            self.app.write_form.fill_sample(sample)
            self.app.write_form.submit()
            self._wait_for_ui_idle()

        self.assertEqual(self.state.update_calls, 10)

        read_result = get_latest_readings(results=10, config=self.config)
        self.assertTrue(read_result.ok)
        self.assertEqual(len(read_result.records), 10)

        for idx, (expected, actual) in enumerate(zip(samples, read_result.records), start=1):
            self.assertEqual(actual.entry_id, idx)
            for spec in FORM_FIELDS:
                self.assertAlmostEqual(
                    getattr(actual, spec.field_key),
                    float(expected[spec.field_key]),
                )

        if len(self.app.history_view.tree.get_children()) != 10:
            self.app.history_view.refresh()
            self._wait_for_ui_idle()

        self.assertEqual(len(self.app.history_view.tree.get_children()), 10)
        if hasattr(self.app.history_view, "diagnostic_level"):
            self.assertEqual(self.app.history_view.diagnostic_level, "CRITICO")
        if hasattr(self.app, "charts_view"):
            self.assertIn("Muestras: 10", self.app.charts_view.stats_var.get())

    def test_rejected_write_and_http_error_preserve_previous_history(self) -> None:
        samples = load_test_samples()
        assert self.app.write_form.writer is not None
        self.app.write_form.writer.cooldown_sec = 0.0  # type: ignore[attr-defined]

        self.app.write_form.fill_sample(samples[0])
        self.app.write_form.submit()
        self._wait_for_ui_idle()

        if len(self.app.history_view.tree.get_children()) != 1:
            self.app.history_view.refresh()
            self._wait_for_ui_idle()
        self.assertEqual(len(self.app.history_view.tree.get_children()), 1)

        # ThingSpeak devuelve 0 (escritura rechazada)
        self.state.force_zero = True
        self.app.write_form.fill_sample(samples[1])
        self.app.write_form.submit()
        self._wait_for_ui_idle()
        self.assertIn("respuesta 0", self.app.write_form.message_var.get())
        self.assertEqual(self.app.write_form.vars["field1"].get(), samples[1]["field1"])

        # Fallo HTTP 503 al consultar histórico conserva la tabla previa
        self.state.force_status = 503
        self.app.history_view.refresh()
        self._wait_for_ui_idle()
        self.assertIn("HTTP 503", self.app.history_view.message_var.get())
        self.assertEqual(len(self.app.history_view.tree.get_children()), 1)


class LiveThingSpeakChannelTests(unittest.TestCase):
    def test_live_public_channel_read_if_online(self) -> None:
        try:
            with socket.create_connection(("api.thingspeak.com", 443), timeout=3.0):
                pass
        except OSError as exc:
            self.skipTest(f"Sin acceso de red a api.thingspeak.com: {exc}")

        result = get_latest_readings(results=10, channel_id=DEFAULT_CHANNEL_ID, timeout=8.0)
        self.assertTrue(result.ok, f"Fallo al leer el canal real: {result.error_message}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.channel_id, DEFAULT_CHANNEL_ID)


if __name__ == "__main__":
    unittest.main()
