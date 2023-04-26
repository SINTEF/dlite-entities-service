"""config subcommand for dlite-entities-service CLI."""
# pylint: disable=duplicate-code
from enum import Enum
from pathlib import Path
from typing import Generator, Optional

try:
    import typer
except ImportError as exc:
    raise ImportError(
        "Please install the DLite entities service utility CLI with "
        f"'pip install {Path(__file__).resolve().parent.parent.parent.resolve()}[cli]'"
    ) from exc

from dotenv import dotenv_values, set_key, unset_key
from rich import print  # pylint: disable=redefined-builtin
from rich.console import Console

from dlite_entities_service.service.config import CONFIG

ERROR_CONSOLE = Console(stderr=True)
CLI_DOTENV_FILE = Path(__file__).resolve().parent / ".env"
SERVICE_DOTENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

APP = typer.Typer(
    name=__file__.rsplit("/", 1)[-1].replace(".py", ""),
    no_args_is_help=True,
    invoke_without_command=True,
)

STATUS = {"use_service_dotenv": False}


class ConfigFields(str, Enum):
    """Configuration options."""

    BASE_URL = "base_url"
    MONGO_URI = "mongo_uri"
    MONGO_USER = "mongo_user"
    MONGO_PASSWORD = "mongo_password"  # nosec

    @classmethod
    def autocomplete(cls, incomplete: str) -> Generator[tuple[str, str], None, None]:
        """Return a list of valid configuration options."""
        for member in cls:
            if member.value.startswith(incomplete):
                if member.value not in CONFIG.__fields__:
                    raise typer.BadParameter(
                        f"Invalid configuration option: {member.value!r}"
                    )
                yield member.value, CONFIG.__fields__[
                    member.value
                ].field_info.description

    def is_sensitive(self) -> bool:
        """Return True if this is a sensitive configuration option."""
        return self in [ConfigFields.MONGO_PASSWORD]


@APP.command(name="set")
def set_config(
    key: ConfigFields = typer.Argument(
        ...,
        help=(
            "Configuration option to set. These can also be set as an environment "
            f"variable by prefixing with {CONFIG.Config.env_prefix!r}."
        ),
        show_choices=True,
        # Start using shell_complete once tiangolo/typer#334 is resolved.
        # shell_complete=ConfigFields.autocomplete,
        autocompletion=ConfigFields.autocomplete,
        case_sensitive=False,
        show_default=False,
    ),
    value: Optional[str] = typer.Argument(
        None,
        help=(
            "Value to set. For sensitive values, this will be prompted for if not "
            "provided."
        ),
        show_default=False,
    ),
) -> None:
    """Set a configuration option."""
    if not value:
        value = typer.prompt(f"Enter value for {key}", hide_input=key.is_sensitive())
    if STATUS["use_service_dotenv"]:
        dotenv_file = SERVICE_DOTENV_FILE
    else:
        dotenv_file = CLI_DOTENV_FILE
    if not dotenv_file.exists():
        dotenv_file.touch()
    set_key(dotenv_file, key, value)
    print(
        f"Set {key} to sensitive value."
        if key.is_sensitive()
        else f"Set {key} to {value}."
    )


@APP.command()
def unset(
    key: ConfigFields = typer.Argument(
        ...,
        help="Configuration option to unset.",
        show_choices=True,
        # Start using shell_complete once tiangolo/typer#334 is resolved.
        # shell_complete=ConfigFields.autocomplete,
        autocompletion=ConfigFields.autocomplete,
        case_sensitive=False,
        show_default=False,
    ),
) -> None:
    """Unset a configuration option."""
    if STATUS["use_service_dotenv"]:
        dotenv_file = SERVICE_DOTENV_FILE
    else:
        dotenv_file = CLI_DOTENV_FILE
    if dotenv_file.exists():
        unset_key(dotenv_file, key)
    print(f"Unset {key}.")


@APP.command()
def show(
    reveal_sensitive: bool = typer.Option(
        False,
        "--reveal-sensitive",
        help="Reveal sensitive values. (DANGEROUS! Use with caution.)",
        is_flag=True,
        show_default=False,
    ),
) -> None:
    """Show the current configuration."""
    if STATUS["use_service_dotenv"]:
        dotenv_file = SERVICE_DOTENV_FILE
    else:
        dotenv_file = CLI_DOTENV_FILE
    if dotenv_file.exists():
        values = {
            ConfigFields(key): value
            for key, value in dotenv_values(dotenv_file).items()
            if key in ConfigFields.__members__
        }
    else:
        ERROR_CONSOLE.print(f"No {dotenv_file} file found.")
        raise typer.Exit(1)

    for key, value in values.items():
        if not reveal_sensitive and key.is_sensitive():
            value = "***"
        print(f"[bold]{key}[/bold]: {value}")


@APP.callback()
def main(
    use_service_dotenv: bool = typer.Option(
        False,
        "--use-service-dotenv/--use-cli-dotenv",
        help=(
            "Use the .env file also used for the DLite Entities Service or one only "
            "for the CLI."
        ),
        is_flag=True,
    ),
    unset_all: bool = typer.Option(
        False,
        "--unset-all",
        help="Unset (remove) all configuration options in dotenv file.",
        show_default=False,
        is_flag=True,
    ),
) -> None:
    """Set DLite entities service configuration options."""
    STATUS["use_service_dotenv"] = use_service_dotenv

    if unset_all:
        typer.confirm(
            "Are you sure you want to unset (remove) all configuration options in "
            f"{'Service' if use_service_dotenv else 'CLI'}-specific .env file?",
            abort=True,
        )

        if use_service_dotenv:
            dotenv_file = SERVICE_DOTENV_FILE
        else:
            dotenv_file = CLI_DOTENV_FILE

        if dotenv_file.exists():
            dotenv_file.unlink()
            print(f"Removed {dotenv_file}.")
        else:
            print(f"No {dotenv_file} file found.")