"""
Pruebas unitarias para el módulo de escritura (P3-04).
Cubre validación de campos, respuesta válida, respuesta 0, errores HTTP, timeout y cadencia (15s).
"""

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.services.writer import ThingSpeakWriter, validate_reactor_sample


def test_validate_sample_valid():
    sample, err = validate_reactor_sample("75.5", 92, "88.0", 12, 4500)
    assert err is None
    assert sample is not None
    assert sample.core_load == 75.5
    assert sample.field_stability == 92.0
    assert sample.coolant_flow == 88.0
    assert sample.jarvis_latency == 12.0
    assert sample.repulsor_power == 4500.0


@pytest.mark.parametrize(
    "f1,f2,f3,f4,f5,expected_msg",
    [
        ("abc", 50, 50, 10, 100, "Carga del núcleo (field1)"),
        (50, -1, 50, 10, 100, "estabilidad del campo (field2) debe estar entre 0 y 100"),
        (50, 100.1, 50, 10, 100, "estabilidad del campo (field2) debe estar entre 0 y 100"),
        (50, 50, -0.5, 10, 100, "flujo de refrigerante (field3) debe estar entre 0 y 100"),
        (50, 50, 105, 10, 100, "flujo de refrigerante (field3) debe estar entre 0 y 100"),
        (50, 50, 50, None, 100, "Latencia JARVIS (field4)"),
        (50, 50, 50, 10, "", "Consumo de repulsores (field5)"),
    ],
)
def test_validate_sample_invalid_inputs(f1, f2, f3, f4, f5, expected_msg):
    sample, err = validate_reactor_sample(f1, f2, f3, f4, f5)
    assert sample is None
    assert err is not None
    assert expected_msg in err


def test_send_sample_missing_api_key():
    writer = ThingSpeakWriter(write_api_key="", base_url="https://api.thingspeak.com")
    result = writer.send_sample(80, 90, 85, 15, 3200)
    assert result.success is False
    assert "THINGSPEAK_WRITE_API_KEY" in (result.error_message or "")


@patch("src.services.writer.requests.get")
def test_send_sample_success_and_cooldown(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "42"
    mock_get.return_value = mock_resp

    writer = ThingSpeakWriter(
        write_api_key="TESTKEY123456789",
        base_url="https://api.thingspeak.com",
        cooldown_sec=15.0,
    )

    # Primer envío: debe tener éxito
    res1 = writer.send_sample(78.2, 95.0, 88.5, 14.0, 5100.0)
    assert res1.success is True
    assert res1.entry_id == 42
    assert res1.cooldown_remaining == 15.0
    assert mock_get.call_count == 1

    # Segundo envío inmediato: debe bloquearse por intervalo de 15 s sin llamar a la red
    res2 = writer.send_sample(79.0, 94.0, 87.0, 15.0, 5200.0)
    assert res2.success is False
    assert res2.cooldown_remaining > 0
    assert "intervalo" in (res2.error_message or "").lower()
    assert mock_get.call_count == 1  # No se hizo segunda llamada HTTP


@patch("src.services.writer.requests.get")
def test_send_sample_thingspeak_zero_response(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "0"
    mock_get.return_value = mock_resp

    writer = ThingSpeakWriter(write_api_key="TESTKEY123456789")
    result = writer.send_sample(70, 80, 80, 10, 1000)

    assert result.success is False
    assert result.entry_id is None
    assert "respuesta 0" in (result.error_message or "").lower()
    assert writer.get_cooldown_remaining() == 0.0


@patch("src.services.writer.requests.get")
def test_send_sample_timeout(mock_get):
    mock_get.side_effect = requests.Timeout("Connection timed out")

    writer = ThingSpeakWriter(write_api_key="TESTKEY123456789")
    result = writer.send_sample(70, 80, 80, 10, 1000)

    assert result.success is False
    assert "timeout" in (result.error_message or "").lower()


@patch("src.services.writer.requests.get")
def test_send_sample_http_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_get.return_value = mock_resp

    writer = ThingSpeakWriter(write_api_key="TESTKEY123456789")
    result = writer.send_sample(70, 80, 80, 10, 1000)

    assert result.success is False
    assert result.http_status == 500
    assert "500" in (result.error_message or "")