# tests/unit/framework/test_errors.py
from __future__ import annotations

import httpx

from seedaudio_cli.framework.errors import CliError, exit_code_for, translate


def test_exit_codes_table() -> None:
    assert exit_code_for("INVALID_INPUT") == 2
    assert exit_code_for("CONFIG_MISSING") == 2
    assert exit_code_for("IO_ERROR") == 3
    assert exit_code_for("API_ERROR") == 4
    assert exit_code_for("NETWORK_ERROR") == 5
    assert exit_code_for("INTERNAL") == 10
    assert exit_code_for("UNKNOWN") == 10


def test_translate_passthrough_clierror() -> None:
    err = CliError("INVALID_INPUT", "x")
    assert translate(err) is err


def test_translate_network() -> None:
    assert translate(httpx.ConnectError("boom")).code == "NETWORK_ERROR"
    assert translate(httpx.ReadTimeout("slow")).code == "NETWORK_ERROR"


def test_translate_io() -> None:
    assert translate(FileNotFoundError("missing")).code == "IO_ERROR"


def test_translate_internal() -> None:
    assert translate(ValueError("weird")).code == "INTERNAL"
