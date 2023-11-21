#!/usr/bin/env python

import logging
from rsa import key, encrypt, decrypt, newkeys
from socketserver import ForkingTCPServer, BaseRequestHandler
from src.bank import Bank
from sys import argv, exit


class Formatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "[DEBUG] %(asctime)s - %(message)s",
        logging.INFO: "[INFO]  %(asctime)s - %(message)s",
        logging.WARNING: "[WARN]  %(asctime)s - %(message)s",
        logging.ERROR: "[ERROR] %(asctime)s - %(message)s",
        logging.CRITICAL: "[CRIT]  %(asctime)s - %(message)s",
    }

    def format(self, record):
        log_format = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_format, datefmt="%d-%m-%Y %H:%M:%S")
        return formatter.format(record)


class Command:
    def __init__(self, command: str, arguments: list):
        self.__command = command
        self.__arguments = arguments
        self.__fn = self.no_fn

        match self.__command:
            case "LOGIN":
                self.__fn = BANK.login

            case "REGISTER":
                self.__fn = BANK.register

            case "DEPOSIT":
                self.__fn = BANK.deposit

            case _:
                self.__arguments = []

    def debug(self):
        if self.fn != self.no_fn:
            LOGGER.debug(
                f"{self.__command} executed",
            )

    def no_fn(self, _=None) -> tuple[int, str]:
        return 254, ""

    def fn(self) -> tuple[int, str]:
        self.__error_code, data = self.__fn(*self.__arguments)
        if self.__error_code == 0:
            return 0, data
        return self.__error_code, ""


class BankServerHandler(BaseRequestHandler):
    def handle_error(self, error_code: int):
        error_msg = f"Error {error_code}: "
        match error_code:
            case 1:
                error_msg += "Invalid login"
            case 2:
                error_msg += "Invalid registration"
            case 3:
                error_msg += "Insufficient funds"
            case 252:
                error_msg += "UUID not found"
            case 253:
                error_msg += "Bad arguments"
            case 254:
                error_msg += "Unknown command"
            case 255:
                error_msg += "Unknown error"

        LOGGER.error(error_msg)

    def send_error_code(self, error_code=255):
        self.request.sendall(f"ERR {error_code}\r\n".encode("utf-8"))

    def send_ok_data(self, ok_data=""):
        self.request.sendall(f"OK {ok_data}\r\n".encode("utf-8"))

    def handle_pre_login(self, data: str) -> bool:
        logged_in = False

        command, *arguments = data.split()
        cmd = Command(command, arguments)
        cmd.debug()
        LOGGER.info(f"Command {command} issued by {self.client_address}")

        # If any error
        error_code, cmd_return = cmd.fn()
        if error_code != 0:
            self.handle_error(error_code)
            self.send_error_code(error_code)
            return logged_in

        # If the command was login, and there was no error, it means a user logged in
        if command == "LOGIN":
            username = arguments[0]
            self.send_ok_data(cmd_return)
            LOGGER.info(f"User {username} has logged in")
            logged_in = True
            return logged_in

        # If the command was register, and there was no error, send an OK message
        if command == "REGISTER":
            self.send_ok_data()

        return logged_in

    def handle_post_login(self, data: str) -> bool:
        command, *arguments = data.split()
        LOGGER.info(f"Command {command} issued by {self.client_address}")

        cmd = Command(command, arguments)
        cmd.debug()

        # If any error
        error_code, _ = cmd.fn()
        if error_code != 0:
            self.handle_error(error_code)
            self.send_error_code(error_code)

        # And the command was login, it means a user logged in
        return not command == "LOGOUT"

    def handle(self):
        LOGGER.info(f"Accepted connection from {self.client_address}")
        SOCKETS_LIST.append(self.client_address)

        # Read data from buffer
        data = self.request.recv(4096).decode("utf-8")

        # Handle pre-login
        logged = self.handle_pre_login(data)

        if logged:
            while True:
                # Read data from buffer
                data = self.request.recv(4096).decode("utf-8")
                logged = self.handle_post_login(data)

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
    # Enable debugging and configure it
    LOGGER = setup_logger()

    if len(argv) < 3 or len(argv) > 5:
        LOGGER.info(
            "Usage: server.py <server_IP> <port> <private_key_path> <public_key_path>"
        )
        exit(1)

    SERVER_IP, PORT = argv[1:3]

    if len(argv) == 3:
        (PUBLIC_KEY, PRIVATE_KEY) = newkeys(2048)
    else:
        PRIVATE_KEY_PATH, PUBLIC_KEY_PATH = argv[3:5]

        with open(PRIVATE_KEY_PATH, "rb") as PRIVATE_KEY_FILE:
            PRIVATE_KEY = key.PrivateKey.load_pkcs1(PRIVATE_KEY_FILE.read())

        with open(PUBLIC_KEY_PATH, "rb") as PUBLIC_KEY_FILE:
            PUBLIC_KEY = key.PublicKey.load_pkcs1(PUBLIC_KEY_FILE.read())

    global PUBLIC_KEY_PEM, SOCKETS_LIST, PUBLIC_KEYS_LIST, UUID_LIST, BANK
    PUBLIC_KEY_PEM = PUBLIC_KEY.save_pkcs1()
    SOCKETS_LIST = []
    PUBLIC_KEYS_LIST = {}
    UUID_LIST = {}
    BANK = Bank()

    SERVER = ForkingTCPServer((SERVER_IP, int(PORT)), BankServerHandler)
    LOGGER.info(f"Server listening on {SERVER_IP}:{PORT}")

    try:
        SERVER.serve_forever()
    except KeyboardInterrupt:
        print("")
        LOGGER.warning("Stopping server, please wait...")
        SERVER.shutdown()
