"""Pruebas unitarias e integración simulada del servicio de lectura (P2-04).

Cubre los escenarios definidos en TASKS.md para Persona 2 (`role:read`):
1. Respuesta válida (incluyendo las 10 muestras oficiales de `data/reactor_samples.csv`).
2. Canal sin registros (`feeds: []`).
3. Campos ausentes, nulos (`None`), cadenas vacías y valores no numéricos.
4. Fallos de red/API (timeout, error de conexión, códigos HTTP 400/401/404/429/500 y JSON inválido).
5. Construcción de URL, paso de `results` y configuración desde `.env`.

Compatible tanto con `pytest` como con `python3 -m unittest`.
"""

from __future__ import annotations

import csv
import json
import os
import socket
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from src.config import PROJECT_ROOT, ThingSpeakConfig
from src.services.read_service import (
    FIELD_SPECS,
    ReactorReading,
    ReadResult,
    build_feeds_url,
    fetch_channel_feeds,
    format_timestamp,
    get_latest_readings,
    normalize_feed_entry,
    normalize_feeds,
    parse_numeric_field,
)


def _load_csv_samples_as_thingspeak_payload() -> dict:
    """Construye un payload JSON idéntico al de ThingSpeak a partir de `data/reactor_samples.csv`."""
    csv_path = PROJECT_ROOT / "data" / "reactor_samples.csv"
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        feeds = []
        for idx, row in enumerate(reader, start=1):
            feeds.append(
                {
                    "created_at": f"2026-11-08T17:{idx:02d}:00Z",
                    "entry_id": idx,
                    "field1": row["field1"],
                    "field2": row["field2"],
                    "field3": row["field3"],
                    "field4": row["field4"],
                    "field5": row["field5"],
                }
            )
    return {
        "channel": {
            "id": 3566091,
            "name": "Stark Industries - Arc Reactor Monitoring",
            "field1": "Core Energy Load",
            "field2": "Field Stability",
            "field3": "Vibranium Coolant Flow",
            "field4": "JARVIS Protocol Latency",
            "field5": "Repulsor Power Consumption",
        },
        "feeds": feeds,
    }


class TestReadServiceContractAndNormalization(unittest.TestCase):
    """Pruebas del contrato de datos (P2-01) y normalización JSON (P2-03)."""

    def test_field_specs_define_five_reactor_variables(self) -> None:
        self.assertEqual(len(FIELD_SPECS), 5)
        self.assertEqual(
            [spec.field_key for spec in FIELD_SPECS],
            ["field1", "field2", "field3", "field4", "field5"],
        )
        self.assertEqual(
            [spec.semantic_key for spec in FIELD_SPECS],
            [
                "core_load",
                "field_stability",
                "coolant_flow",
                "jarvis_latency",
                "repulsor_power",
            ],
        )

    def test_parse_numeric_field_valid_and_invalid_inputs(self) -> None:
        self.assertEqual(parse_numeric_field("52.4"), 52.4)
        self.assertEqual(parse_numeric_field("  96.8  "), 96.8)
        self.assertEqual(parse_numeric_field(100), 100.0)
        self.assertEqual(parse_numeric_field(0), 0.0)
        self.assertEqual(parse_numeric_field("-12.5"), -12.5)

        # Casos nulos, vacíos o inválidos -> None
        for invalid in (None, "", "   ", "null", "None", "NaN", "inf", "-inf", "abc", True, False, [], {}):
            with self.subTest(invalid=invalid):
                self.assertIsNone(parse_numeric_field(invalid))

    def test_normalize_valid_ten_samples_from_csv(self) -> None:
        payload = _load_csv_samples_as_thingspeak_payload()
        records = normalize_feeds(payload)

        self.assertEqual(len(records), 10)
        first = records[0]
        self.assertIsInstance(first, ReactorReading)
        self.assertEqual(first.entry_id, 1)
        self.assertEqual(first.created_at, "2026-11-08T17:01:00Z")
        self.assertEqual(first.formatted_timestamp, "2026-11-08 17:01:00 UTC")
        self.assertEqual(first.field1, 52.4)
        self.assertEqual(first.field2, 96.8)
        self.assertEqual(first.field3, 35.2)
        self.assertEqual(first.field4, 118.6)
        self.assertEqual(first.field5, 42.3)

        # Propiedades semánticas y exportación a diccionario
        self.assertEqual(first.core_load, 52.4)
        self.assertEqual(first.field_stability, 96.8)
        self.assertEqual(first.coolant_flow, 35.2)
        self.assertEqual(first.jarvis_latency, 118.6)
        self.assertEqual(first.repulsor_power, 42.3)

        as_dict = first.to_dict()
        self.assertEqual(as_dict["entry_id"], 1)
        self.assertEqual(as_dict["field1"], 52.4)
        self.assertEqual(as_dict["core_load"], 52.4)
        self.assertEqual(as_dict["formatted_timestamp"], "2026-11-08 17:01:00 UTC")

        last = records[-1]
        self.assertEqual(last.entry_id, 10)
        self.assertEqual(last.field1, 95.8)
        self.assertEqual(last.field2, 67.9)
        self.assertEqual(last.field3, 96.4)
        self.assertEqual(last.field4, 249.8)
        self.assertEqual(last.field5, 94.1)

    def test_normalize_empty_channel_returns_empty_list(self) -> None:
        payload = {"channel": {"id": 3566091, "name": "Stark Reactor"}, "feeds": []}
        self.assertEqual(normalize_feeds(payload), [])
        self.assertEqual(normalize_feeds(None), [])
        self.assertEqual(normalize_feeds({}), [])

    def test_normalize_missing_and_null_fields(self) -> None:
        raw_entry = {
            "entry_id": "7",
            "created_at": "2026-11-08T18:00:00Z",
            "field1": "79.8",
            "field2": None,
            "field3": "",
            "field4": "ERROR_SENSOR",
            # field5 ausente en el JSON
        }
        reading = normalize_feed_entry(raw_entry)
        self.assertIsNotNone(reading)
        assert reading is not None
        self.assertEqual(reading.entry_id, 7)
        self.assertEqual(reading.field1, 79.8)
        self.assertIsNone(reading.field2)
        self.assertIsNone(reading.field3)
        self.assertIsNone(reading.field4)
        self.assertIsNone(reading.field5)

    def test_normalize_discards_entries_without_valid_entry_id_and_sorts_records(self) -> None:
        feeds = [
            {"entry_id": 3, "created_at": "2026-11-08T17:03:00Z", "field1": "63.9"},
            {"entry_id": None, "created_at": "2026-11-08T17:00:00Z", "field1": "10.0"},
            {"created_at": "2026-11-08T17:00:00Z", "field1": "20.0"},
            {"entry_id": 1, "created_at": "2026-11-08T17:01:00Z", "field1": "52.4"},
            {"entry_id": 2, "created_at": "2026-11-08T17:02:00Z", "field1": "58.7"},
        ]
        records = normalize_feeds(feeds)
        self.assertEqual([r.entry_id for r in records], [1, 2, 3])
        self.assertEqual([r.field1 for r in records], [52.4, 58.7, 63.9])

    def test_format_timestamp_handles_iso_and_fallback(self) -> None:
        self.assertEqual(format_timestamp("2026-11-08T17:15:30Z"), "2026-11-08 17:15:30 UTC")
        self.assertEqual(format_timestamp(""), "")
        self.assertEqual(format_timestamp(None), "")
        self.assertEqual(format_timestamp("fecha-no-iso"), "fecha-no-iso")


class TestReadServiceHttpAndErrors(unittest.TestCase):
    """Pruebas de peticiones GET a ThingSpeak y gestión de fallos (P2-02 y P2-04)."""

    def test_build_feeds_url_includes_results_and_optional_api_key(self) -> None:
        url_public = build_feeds_url(channel_id="3566091", results=10)
        self.assertEqual(
            url_public,
            "https://api.thingspeak.com/channels/3566091/feeds.json?results=10",
        )

        url_with_key = build_feeds_url(
            channel_id="3566091",
            results=5,
            api_key="SECRET_READ_KEY",
            base_url="https://api.thingspeak.com/",
        )
        self.assertEqual(
            url_with_key,
            "https://api.thingspeak.com/channels/3566091/feeds.json?results=5&api_key=SECRET_READ_KEY",
        )

    def test_get_latest_readings_success(self) -> None:
        payload = _load_csv_samples_as_thingspeak_payload()
        captured_calls: list[tuple[str, float]] = []

        def fake_http_get(url: str, timeout: float) -> tuple[int, str]:
            captured_calls.append((url, timeout))
            return 200, json.dumps(payload)

        result = get_latest_readings(
            results=10,
            channel_id="3566091",
            api_key=None,
            timeout=8.0,
            http_get=fake_http_get,
        )

        self.assertTrue(result.ok)
        self.assertFalse(result.is_empty)
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.channel_id, "3566091")
        self.assertEqual(result.channel_name, "Stark Industries - Arc Reactor Monitoring")
        self.assertEqual(len(result.records), 10)
        self.assertEqual(len(captured_calls), 1)
        self.assertIn("channels/3566091/feeds.json?results=10", captured_calls[0][0])
        self.assertEqual(captured_calls[0][1], 8.0)

    def test_get_latest_readings_empty_channel(self) -> None:
        empty_payload = {
            "channel": {"id": 3566091, "name": "Stark Industries - Arc Reactor Monitoring"},
            "feeds": [],
        }

        result = get_latest_readings(
            results=5,
            channel_id="3566091",
            http_get=lambda url, timeout: (200, json.dumps(empty_payload)),
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.is_empty)
        self.assertEqual(result.records, [])
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.error_message)

    def test_http_error_codes_are_reported_clearly(self) -> None:
        scenarios = [
            (400, "HTTP 400"),
            (401, "HTTP 401"),
            (403, "HTTP 403"),
            (404, "HTTP 404"),
            (429, "HTTP 429"),
            (500, "HTTP 500"),
            (503, "HTTP 503"),
        ]
        for status_code, expected_fragment in scenarios:
            with self.subTest(status_code=status_code):
                result = get_latest_readings(
                    results=10,
                    channel_id="3566091",
                    http_get=lambda url, timeout, code=status_code: (code, '{"error":"fail"}'),
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.status_code, status_code)
                self.assertEqual(result.records, [])
                self.assertIsNotNone(result.error_message)
                assert result.error_message is not None
                self.assertIn(expected_fragment, result.error_message)

    def test_network_timeout_is_reported(self) -> None:
        def raise_timeout(url: str, timeout: float) -> tuple[int, str]:
            raise urllib.error.URLError(socket.timeout("timed out"))

        result = get_latest_readings(
            results=10,
            channel_id="3566091",
            timeout=5.0,
            http_get=raise_timeout,
        )
        self.assertFalse(result.ok)
        self.assertIsNone(result.status_code)
        self.assertEqual(result.records, [])
        self.assertIsNotNone(result.error_message)
        assert result.error_message is not None
        self.assertIn("Tiempo de espera agotado", result.error_message)

    def test_connection_error_is_reported(self) -> None:
        def raise_connection_error(url: str, timeout: float) -> tuple[int, str]:
            raise ConnectionError("No route to host")

        result = get_latest_readings(
            results=10,
            channel_id="3566091",
            http_get=raise_connection_error,
        )
        self.assertFalse(result.ok)
        self.assertIsNone(result.status_code)
        self.assertEqual(result.records, [])
        self.assertIsNotNone(result.error_message)
        assert result.error_message is not None
        self.assertIn("Error de conexión", result.error_message)

    def test_invalid_json_or_missing_feeds_key_is_reported(self) -> None:
        bad_json_result = fetch_channel_feeds(
            channel_id="3566091",
            http_get=lambda url, timeout: (200, "<html>502 Bad Gateway</html>"),
        )
        self.assertFalse(bad_json_result.ok)
        self.assertEqual(bad_json_result.status_code, 200)
        self.assertIsNotNone(bad_json_result.error_message)
        assert bad_json_result.error_message is not None
        self.assertIn("JSON válido", bad_json_result.error_message)

        missing_feeds_result = fetch_channel_feeds(
            channel_id="3566091",
            http_get=lambda url, timeout: (200, '{"channel": {"id": 3566091}}'),
        )
        self.assertFalse(missing_feeds_result.ok)
        self.assertEqual(missing_feeds_result.status_code, 200)
        self.assertIsNotNone(missing_feeds_result.error_message)
        assert missing_feeds_result.error_message is not None
        self.assertIn("feeds", missing_feeds_result.error_message)

    def test_invalid_arguments_return_controlled_error(self) -> None:
        bad_results = fetch_channel_feeds(channel_id="3566091", results=0)
        self.assertFalse(bad_results.ok)
        self.assertIn("results", bad_results.error_message or "")

        bad_channel = fetch_channel_feeds(channel_id="   ", results=5)
        self.assertFalse(bad_channel.ok)
        self.assertIn("channel_id", bad_channel.error_message or "")

        bad_timeout = fetch_channel_feeds(channel_id="3566091", results=5, timeout=-1)
        self.assertFalse(bad_timeout.ok)
        self.assertIn("timeout", bad_timeout.error_message or "")

    def test_config_loads_from_dotenv_and_ignores_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "THINGSPEAK_CHANNEL_ID=3566091\n"
                "THINGSPEAK_WRITE_API_KEY=LJIWWBTEV...\n"
                "THINGSPEAK_READ_API_KEY=REEMPLAZAR\n"
                "THINGSPEAK_BASE_URL=https://api.thingspeak.com/\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                cfg = ThingSpeakConfig.from_env(env_file)
                self.assertEqual(cfg.channel_id, "3566091")
                self.assertIsNone(cfg.read_api_key)
                self.assertIsNone(cfg.write_api_key)
                self.assertEqual(cfg.base_url, "https://api.thingspeak.com")


if __name__ == "__main__":
    unittest.main()
