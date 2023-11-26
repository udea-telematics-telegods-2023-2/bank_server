#!/usr/bin/env python
import logging
from socket import socket
from socketserver import ForkingTCPServer, ForkingUDPServer, BaseRequestHandler
from src.bank import Bank
from sys import argv, exit
from random import randint
from threading import Thread


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


class Command:
    """
    Represents a command for the banking application with associated functions.

    Attributes:
        __command (str): The command string.
        __arguments (list): The list of arguments for the command.
        __fn (callable): The function associated with the command.
        __error_code (int): The error code resulting from the command execution.

    Methods:
        debug(): Logs a debug message when the command is executed.
        no_fn(_: None) -> tuple[int, str]: Default function for commands without an associated function.
        wrong_args(_: None) -> tuple[int, str]: Function for commands with incorrect arguments.
        __check_args(args_number: int = 0, fn: callable = no_fn): Checks and sets the associated function based on the command.
        fn() -> tuple[int, str]: Executes the associated function and returns the result.

    Notes:
        This class represents a command in the banking application and is associated with specific functions.
        The associated function is determined based on the command string and the number of arguments.
    """

    def debug(self):
        """
        Outputs additional information to the logger.
        """
        if self.fn != self.no_fn:
            LOGGER.debug(
                f"{self.__command} executed",
            )

    def no_fn(self, _=None) -> tuple[int, str]:
        """
        Default function for non-valid commands.
        """
        return 254, ""

    def wrong_args(self, _=None) -> tuple[int, str]:
        """
        Default function for wrong_number of arguments.
        """
        return 253, ""

    def __check_args(self, args_number: int = 0, fn=no_fn):
        """
        Checks if the number of arguments supplied is correct.
        """
        if len(self.__arguments) != args_number:
            self.__arguments = []
            self.__fn = self.wrong_args
        else:
            self.__fn = fn

    def __init__(self, command: str, arguments: list):
        self.__command = command
        self.__arguments = arguments
        self.__fn = self.no_fn

        match self.__command:
            case "LOGIN":
                self.__check_args(args_number=2, fn=BANK.login)

            case "REGISTER":
                self.__check_args(args_number=2, fn=BANK.register)

            case "CHPASSWD":
                self.__check_args(args_number=3, fn=BANK.change_password)

            case "BALANCE":
                self.__check_args(args_number=1, fn=BANK.balance)

            case "DEPOSIT":
                self.__check_args(args_number=2, fn=BANK.deposit)

            case "WITH":
                self.__check_args(args_number=2, fn=BANK.withdraw)

            case "TRANSFER":
                self.__check_args(args_number=3, fn=BANK.transfer)

            case "LOGOUT":
                self.__check_args(args_number=1, fn=BANK.logout)

            case "PAY":
                self.__check_args(args_number=4, fn=BANK.pay)

            case _:
                self.__arguments = []

    def fn(self) -> tuple[int, str]:
        """
        Executes the binded function of the command and returns the error code.
        """
        self.__error_code, data = self.__fn(*self.__arguments)
        if self.__error_code == 0:
            return 0, data
        return self.__error_code, ""


class BankTCPServerHandler(BaseRequestHandler):
    def handle_error(self, error_code: int):
        error_msg = f"Error {error_code}: "
        match error_code:
            case 1:
                error_msg += "Invalid login"
            case 2:
                error_msg += "Invalid registration"
            case 3:
                error_msg += "Insufficient funds"
            case 251:
                error_msg += "Unauthorized access"
            case 252:
                error_msg += "UUID not found"
            case 253:
                error_msg += "Bad arguments"
            case 254:
                error_msg += "Unknown command"
            case 255:
                error_msg += "Unknown error"

        LOGGER.error(error_msg)

    def check_user(self, connected_uuid: str, cmd_uuid: str) -> bool:
        return connected_uuid == cmd_uuid

    def send_error_code(self, error_code=255):
        self.request.sendall(f"ERR {error_code}\r\n".encode("utf-8"))

    def send_ok_data(self, ok_data=""):
        self.request.sendall(f"OK {ok_data}\r\n".encode("utf-8"))

    def handle_pre_login(self, data: str) -> bool:
        # Initializes the logged_in flag
        logged_in = False

        # Extracts command and data from input
        command, *arguments = data.split()
        cmd = Command(command, arguments)
        cmd.debug()
        LOGGER.info(f"Command {command} issued by {self.client_address}")

        # Handle any error and send error code to client
        error_code, cmd_return = cmd.fn()
        if error_code != 0:
            self.handle_error(error_code)
            self.send_error_code(error_code)
            return logged_in

        # If the command was login, and there was no error, it means a user logged in
        if command == "LOGIN":
            # Replies with UUID
            self.send_ok_data(cmd_return)

            # Updates connected_users dictionary
            global connected_users
            connected_users[self.client_address] = cmd_return

            # Logs login event and changes the flag
            self.username = arguments[0]
            self.uuid = cmd_return
            LOGGER.info(f"User {self.username} has logged in")
            logged_in = True
            return logged_in

        # If the command was register, and there was no error, send an OK message
        if command == "REGISTER":
            self.send_ok_data()

        return logged_in

    def handle_logout(self, client_address: str) -> bool:
        # Removes connected_users entry for current session and logs the event
        global connected_users
        del connected_users[client_address]
        LOGGER.info(f"User {self.username} has logged out")
        return True

    def handle_post_login(self, data: str) -> bool:
        # Extracts command and data from input
        command, *arguments = data.split()
        LOGGER.info(
            f"Command {command} issued by {self.username}:{self.client_address}"
        )

        # Sets connected UUID as argument if not given by client
        if arguments == []:
            arguments = [self.uuid]

        cmd = Command(command, arguments)
        cmd.debug()

        # Check connected user and command UUID
        if not self.check_user(arguments[0], connected_users[self.client_address]):
            error_code = 251
            self.handle_error(error_code)
            self.send_error_code(error_code)
            return False

        # Handle other errors
        error_code, cmd_return = cmd.fn()
        if error_code != 0:
            self.handle_error(error_code)
            self.send_error_code(error_code)
            return False

        # If no errors, answer with OK
        self.send_ok_data(cmd_return)

        # Handle logout
        if command == "LOGOUT":
            return self.handle_logout(self.client_address)

        return False

    def handle(self):
        LOGGER.info(f"Accepted connection from {self.client_address}")
        logged = False
        logout = False

        while not logout:
            if not logged:
                # Read data from buffer
                data = self.request.recv(4096).decode("utf-8")

                # Checks non-empty message
                if len(data) <= 2:
                    LOGGER.warning("Empty message")
                    continue

                # Handle pre-login
                logged = self.handle_pre_login(data)
            else:
                # Read data from buffer
                data = self.request.recv(4096)

                # Checks non-empty message
                if len(data) <= 2:
                    LOGGER.warning("Empty message")

                # Check if client disconnected
                if not data:
                    break

                logout = self.handle_post_login(data.decode("utf-8"))

        self.finish()


class BankUDPServerHandler(BaseRequestHandler):
    def handle_error(self, error_code: int):
        error_msg = f"Error {error_code}: "
        match error_code:
            case 1:
                error_msg += "Invalid login"
            case 2:
                error_msg += "Invalid registration"
            case 3:
                error_msg += "Insufficient funds"
            case 251:
                error_msg += "Unauthorized access"
            case 252:
                error_msg += "UUID not found"
            case 253:
                error_msg += "Bad arguments"
            case 254:
                error_msg += "Unknown command"
            case 255:
                error_msg += "Unknown error"

        LOGGER.error(error_msg)

    def encrypt(self, msg: str, n: int) -> str:
        return msg

    def decrypt(self, msg: str, n: int) -> str:
        return msg

    def send_encrypted_data(self, conn, to, n: int, encrypted_msg: str):
        conn.sendto(self.encrypt(f"{encrypted_msg} {n}\r\n", n).encode("utf-8"), to)

    def send_error_code(self, conn, to: socket, n: int, error_code: int = 255):
        self.send_encrypted_data(conn, to, n, self.encrypt(f"ERR {error_code}", n))

    def send_ok_data(self, conn, to: socket, n: int, ok_data: str = ""):
        self.send_encrypted_data(conn, to, n, self.encrypt(f"OK {ok_data}", n))

    def handle(self):
        # Log and get info about the connection
        LOGGER.info(f"Received UDP message from {self.client_address}")
        data, conn = self.request

        # Decode the data and decrypt it
        decoded_data = data.decode("utf-8")
        if len(decoded_data) <= 1:
            LOGGER.warning("Empty message")
            self.finish()
            return
        n = decoded_data.split()[-1]

        # Handle bad cypher decode number
        if not n.isdigit():
            LOGGER.warning("Bad cypher")
            self.finish()
            return

        # Decrypt using the decode number
        decrypted_data = self.decrypt(decoded_data, n)

        # Generate random n for answer
        rand_n = randint(1, 26)
        # n = 0 means no encryption
        rand_n = 0

        # Validate the only command accepted through UDP
        if decrypted_data.startswith("PAY"):
            # Extracts command and data from input
            command, *arguments = decrypted_data.split()

            # Exclude the decryption number
            arguments = arguments[:-1]
            cmd = Command(command, arguments)
            cmd.debug()
            LOGGER.info(f"Command {command} issued by {self.client_address}")

            # Handle any error and send error code to client
            error_code, cmd_return = cmd.fn()
            if error_code != 0:
                self.handle_error(error_code)
                self.send_error_code(conn, self.client_address, rand_n, error_code)
                self.finish()
                return
            # If no error, send OK data
            self.send_ok_data(conn, self.client_address, rand_n, cmd_return)
        # If command is not PAY, send bad argument
        else:
            error_code = 253
            self.send_error_code(conn, self.client_address, rand_n, error_code)
        self.finish()


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


if __name__ == "__main__":
    # Enable logger and configure it
    LOGGER = setup_logger()

    # Check correct number or arguments
    if len(argv) != 3:
        LOGGER.info("Usage: server.py <server_IP> <port>")
        exit(1)

    # Extract arguments
    SERVER_IP, PORT = argv[1:]

    # Declare global variables and initialize them
    global BANK, connected_users
    BANK = Bank()
    connected_users = {}

    # Create servers and their threads
    UDP_SERVER = ForkingUDPServer((SERVER_IP, int(PORT)), BankUDPServerHandler)
    TCP_SERVER = ForkingTCPServer((SERVER_IP, int(PORT)), BankTCPServerHandler)
    udp_thread = Thread(target=UDP_SERVER.serve_forever)
    tcp_thread = Thread(target=TCP_SERVER.serve_forever)

    try:
        # Start the threads
        udp_thread.start()
        LOGGER.info(f"UDP Server listening on {SERVER_IP}:{PORT}")
        tcp_thread.start()
        LOGGER.info(f"TCP Server listening on {SERVER_IP}:{PORT}")

        # Wait for both threads to finish
        tcp_thread.join()
        udp_thread.join()

    except KeyboardInterrupt:
        # Empty print to not have the ^C in the same line as the warn
        print("")
        LOGGER.warning("Stopping server, please wait...")

        # Shutdown both servers
        TCP_SERVER.shutdown()
        UDP_SERVER.shutdown()
