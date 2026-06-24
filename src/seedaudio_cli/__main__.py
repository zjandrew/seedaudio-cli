# src/seedaudio_cli/__main__.py
from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import click

from seedaudio_cli.framework.envelope import Envelope, Success, apply_jq, render
from seedaudio_cli.framework.errors import CliError, exit_code_for, translate

try:
    # Single source of truth: the version declared in pyproject.toml / package metadata.
    __version__ = version("zjandrew-seedaudio-cli")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+local"


class _Root(click.Group):
    """Click group that converts CliError into a JSON envelope so that
    `CliRunner.invoke` tests see the error in stdout. Production callers
    go through `main()` instead, which is the regular top-level handler."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except CliError as exc:
            click.echo(render(exc.to_envelope(), fmt="json"))
            ctx.exit(exit_code_for(exc.code))


@click.group(name="seedaudio-cli", cls=_Root, invoke_without_command=False)
@click.version_option(__version__, prog_name="seedaudio-cli")
@click.option("--endpoint", default=None, help="override endpoint for this invocation")
@click.option("--api-key", default=None, help="override X-Api-Key for this invocation")
@click.option("--resource-id", "resource_id", default=None, help="override X-Api-Resource-Id")
@click.option("--profile", default=None, help="select a saved profile")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--jq", "jq_expr", default=None, help="dotted-path filter on envelope.data")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--yes", is_flag=True, default=False)
@click.pass_context
def root(
    ctx: click.Context,
    endpoint: str | None,
    api_key: str | None,
    resource_id: str | None,
    profile: str | None,
    fmt: str,
    jq_expr: str | None,
    dry_run: bool,
    verbose: bool,
    yes: bool,
) -> None:
    """Volcengine Doubao speech synthesis (TTS) CLI."""
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "endpoint": endpoint,
            "api_key": api_key,
            "resource_id": resource_id,
            "profile": profile,
            "format": fmt,
            "jq": jq_expr,
            "dry_run": dry_run,
            "verbose": verbose,
            "yes": yes,
        }
    )


def emit(ctx: click.Context, env: Envelope) -> None:
    g = ctx.obj
    if isinstance(env, Success) and g.get("jq"):
        env = apply_jq(env, g["jq"])
    out = render(env, fmt=g.get("format") or "json")
    click.echo(out)


def _register_commands() -> None:
    # Commands are imported here (and registered via their own decorators) to
    # keep import side effects out of plain module load.
    from seedaudio_cli.commands import config as _config
    from seedaudio_cli.commands import dialogue as _dialogue
    from seedaudio_cli.commands import synthesize as _synthesize
    from seedaudio_cli.commands import voices as _voices

    root.add_command(_synthesize.synthesize)
    root.add_command(_dialogue.dialogue)
    root.add_command(_voices.voices)
    root.add_command(_config.config)


_register_commands()


def main() -> None:
    try:
        # standalone_mode=False makes click return the exit code (via ctx.exit /
        # click Exit) instead of calling sys.exit itself, so we must honor it —
        # otherwise error exit codes are swallowed and the process always exits 0.
        code = root.main(prog_name="seedaudio-cli", standalone_mode=False)
        sys.exit(code or 0)
    except click.exceptions.UsageError as e:
        click.echo(e.format_message(), err=True)
        sys.exit(2)
    except click.exceptions.Abort:
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:  # top-level translator
        cli_err = translate(exc)
        click.echo(render(cli_err.to_envelope(), fmt="json"), err=True)
        if "--verbose" in sys.argv:
            import traceback

            traceback.print_exc(file=sys.stderr)
        sys.exit(exit_code_for(cli_err.code))


if __name__ == "__main__":
    main()
