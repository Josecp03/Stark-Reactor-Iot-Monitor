"""Pruebas de la configuración y del punto de entrada (P4-01, issue #14).

Compatible con `pytest` y con `python -m unittest`.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import main as main_module
from src.config import DEFAULT_CHANNEL_ID, PROJECT_ROOT, REQUIRED_ENV_VARS, ThingSpeakConfig

FAKE_WRITE_KEY = "TESTWRITEKEY0000"
MISSING_ENV_FILE = Path(tempfile.gettempdir()) / "stark-reactor-no-existe.env"


def _config_from(env: dict[str, str], env_file: Path = MISSING_ENV_FILE) -> ThingSpeakConfig:
    with patch.dict(os.environ, env, clear=True):
        return ThingSpeakConfig.from_env(env_file)


class ConfigFromEnvTests(unittest.TestCase):
    def test_reads_channel_and_write_key_from_environment(self) -> None:
        cfg = _config_from({"THINGSPEAK_CHANNEL_ID": "1234567", "THINGSPEAK_WRITE_API_KEY": FAKE_WRITE_KEY})
        self.assertEqual(cfg.channel_id, "1234567")
        self.assertEqual(cfg.write_api_key, FAKE_WRITE_KEY)
        self.assertEqual(cfg.problems(), [])
        self.assertTrue(cfg.can_write)
        self.assertTrue(cfg.can_read)

    def test_reads_values_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                f"THINGSPEAK_CHANNEL_ID=7654321\nTHINGSPEAK_WRITE_API_KEY={FAKE_WRITE_KEY}\n",
                encoding="utf-8",
            )
            cfg = _config_from({}, env_file)
        self.assertEqual(cfg.channel_id, "7654321")
        self.assertEqual(cfg.write_api_key, FAKE_WRITE_KEY)

    def test_missing_write_key_is_reported_and_blocks_only_writing(self) -> None:
        cfg = _config_from({"THINGSPEAK_CHANNEL_ID": DEFAULT_CHANNEL_ID})
        problems = cfg.problems()
        self.assertEqual([p.variable for p in problems], ["THINGSPEAK_WRITE_API_KEY"])
        self.assertIn(".env", problems[0].message)
        self.assertFalse(cfg.can_write)
        self.assertTrue(cfg.can_read)

    def test_placeholder_write_key_counts_as_missing(self) -> None:
        cfg = _config_from({"THINGSPEAK_WRITE_API_KEY": "REEMPLAZAR"})
        self.assertIsNone(cfg.write_api_key)
        self.assertFalse(cfg.can_write)

    def test_non_numeric_channel_id_is_reported(self) -> None:
        cfg = _config_from({"THINGSPEAK_CHANNEL_ID": "mi-canal", "THINGSPEAK_WRITE_API_KEY": FAKE_WRITE_KEY})
        self.assertEqual([p.variable for p in cfg.problems()], ["THINGSPEAK_CHANNEL_ID"])
        self.assertFalse(cfg.can_read)
        self.assertFalse(cfg.can_write)

    def test_problem_messages_never_contain_the_key(self) -> None:
        cfg = _config_from({"THINGSPEAK_CHANNEL_ID": "abc", "THINGSPEAK_WRITE_API_KEY": FAKE_WRITE_KEY})
        for problem in cfg.problems():
            self.assertNotIn(FAKE_WRITE_KEY, problem.message)


class EnvExampleTests(unittest.TestCase):
    def test_env_example_lists_required_variables_without_real_keys(self) -> None:
        content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        values = dict(
            line.split("=", 1) for line in content.splitlines() if line and not line.startswith("#") and "=" in line
        )
        for name in REQUIRED_ENV_VARS:
            self.assertIn(name, values)
        self.assertEqual(values["THINGSPEAK_WRITE_API_KEY"], "REEMPLAZAR")
        self.assertEqual(values["THINGSPEAK_READ_API_KEY"], "")

    def test_gitignore_excludes_env_file(self) -> None:
        lines = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", lines)
        self.assertIn("!.env.example", lines)


class CheckConfigCommandTests(unittest.TestCase):
    def _run(self, env: dict[str, str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(main_module, "ThingSpeakConfig") as cfg_cls,
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            cfg_cls.from_env.side_effect = lambda: ThingSpeakConfig.from_env(MISSING_ENV_FILE)
            code = main_module.main(["--check-config"])
        return code, out.getvalue(), err.getvalue()

    def test_check_config_fails_with_clear_message_when_write_key_missing(self) -> None:
        code, out, err = self._run({})
        self.assertEqual(code, 1)
        self.assertIn("Write API Key:     NO configurada", out)
        self.assertIn("THINGSPEAK_WRITE_API_KEY", err)

    def test_check_config_succeeds_without_printing_the_key(self) -> None:
        code, out, err = self._run({"THINGSPEAK_WRITE_API_KEY": FAKE_WRITE_KEY})
        self.assertEqual(code, 0)
        self.assertIn("Configuración correcta.", out)
        self.assertNotIn(FAKE_WRITE_KEY, out + err)


if __name__ == "__main__":
    unittest.main()
