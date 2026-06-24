# src/seedaudio_cli/framework/errors.py
from __future__ import annotations

from typing import Any

import httpx

from seedaudio_cli.framework.envelope import Failure

EXIT_CODES: dict[str, int] = {
    "INVALID_INPUT": 2,
    "CONFIG_MISSING": 2,
    "IO_ERROR": 3,
    "API_ERROR": 4,
    "NETWORK_ERROR": 5,
    "INTERNAL": 10,
}


class CliError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_envelope(self) -> Failure:
        return Failure(code=self.code, message=self.message, details=self.details)


def exit_code_for(code: str) -> int:
    return EXIT_CODES.get(code, EXIT_CODES["INTERNAL"])


def translate(exc: Exception) -> CliError:
    if isinstance(exc, CliError):
        return exc
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return CliError("NETWORK_ERROR", str(exc) or exc.__class__.__name__)
    if isinstance(exc, httpx.HTTPError):
        return CliError("NETWORK_ERROR", str(exc) or exc.__class__.__name__)
    if isinstance(exc, (OSError, PermissionError, FileNotFoundError)):
        return CliError("IO_ERROR", str(exc))
    return CliError("INTERNAL", str(exc) or exc.__class__.__name__)
