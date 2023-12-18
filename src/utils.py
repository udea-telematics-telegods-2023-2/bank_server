# Standard library modules
import argparse
import logging
from enum import Enum
from ipaddress import IPv4Address
from pathlib import Path


def get_project_root() -> Path | None:
    current_path = Path(__file__)

    # Iterate until reaching the root directory
    while current_path != current_path.parent:
        if (current_path / "pyproject.toml").is_file():
            return current_path
        current_path = current_path.parent


class Formatter(logging.Formatter):
    """
    Custom log formatter for a more 'pichuki' log output.

    Attributes:
        FORMATS (dict): A mapping of log levels to their respective formats.
            The formats include the log level, timestamp, and log message.
        DATEFMT (str): The date format for the timestamp.

    Methods:
        format(record): Formats a log record into a string.
    """

    FORMATS = {
        logging.DEBUG: "[DEBUG] %(asctime)s (%(name)s) - %(message)s",
        logging.INFO: "[INFO]  %(asctime)s (%(name)s) - %(message)s",
        logging.WARNING: "[WARN]  %(asctime)s (%(name)s) - %(message)s",
        logging.ERROR: "[ERROR] %(asctime)s (%(name)s) - %(message)s",
        logging.CRITICAL: "[CRIT]  %(asctime)s (%(name)s) - %(message)s",
    }

    DATEFMT = "%d-%m-%Y %H:%M:%S"

    def format(self, record) -> str:
        """
        Formats a log record into a string.

        Args:
            record (LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message.

        Notes:
            This method overrides the format method in the logging.Formatter class.
        """
        log_format = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_format, datefmt=self.DATEFMT)
        return formatter.format(record)


def setup_logger(name: str = __name__, verbose: bool = False):
    level = logging.DEBUG if verbose else logging.WARN
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler and set the level to DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # Create a formatter
    formatter = Formatter()

    # Add the formatter to the handler
    ch.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(ch)

    return logger


def setup_parser(**kwargs):
    parser = argparse.ArgumentParser(**kwargs)
    parser.add_argument(
        "--ip_address", default="0.0.0.0", type=IPv4Address, help="Server IP address"
    )
    parser.add_argument("--port", default=8888, type=int, help="Server port")
    parser.add_argument(
        "--dbpath",
        default="./db/bank.db",
        type=Path,
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--certfile",
        default="./credentials/telegods_bank.crt",
        type=Path,
        help="Path to the SSL certificate file",
    )
    parser.add_argument(
        "--keyfile",
        default="./credentials/telegods_bank.key",
        type=Path,
        help="Path to the SSL key file",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")

    args = parser.parse_args()

    # Check if certfile exists
    if not args.certfile.exists():
        parser.error(f"Certfile not found: {args.certfile}")

    # Check if keyfile exists
    if not args.keyfile.exists():
        parser.error(f"Keyfile not found: {args.keyfile}")

    return args


class ErrorCode(Enum):
    # No error
    OK = 0

    # Server errors
    INVALID_REGISTRATION = 1
    INVALID_LOGIN = 2
    SESSION_CONFLICT = 3
    INSUFFICIENT_FUNDS = 4
    INSUFFICIENT_STOCK = 5

    # Client errors
    INVALID_IP = 128
    INVALID_PORT = 129

    # General errors
    UNAUTHORIZED_ACCESS = 251
    UUID_NOT_FOUND = 252
    BAD_ARGUMENTS = 253
    UNKNOWN_COMMAND = 254
    UNKNOWN_ERROR = 255
