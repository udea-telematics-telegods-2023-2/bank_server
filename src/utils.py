import logging
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


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
        logging.DEBUG: "[DEBUG] %(asctime)s - %(message)s",
        logging.INFO: "[INFO]  %(asctime)s - %(message)s",
        logging.WARNING: "[WARN]  %(asctime)s - %(message)s",
        logging.ERROR: "[ERROR] %(asctime)s - %(message)s",
        logging.CRITICAL: "[CRIT]  %(asctime)s - %(message)s",
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


def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create console handler and set the level to DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = Formatter()

    # Add the formatter to the handler
    ch.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(ch)

    return logger
