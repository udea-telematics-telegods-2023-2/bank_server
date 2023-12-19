#!/usr/bin/env python
# Standard library modules
from logging import Logger
import ssl
import socket

from pathlib import Path
from socketserver import (
    ForkingTCPServer,
    ForkingUDPServer,
    StreamRequestHandler,
    DatagramRequestHandler,
)
from threading import Thread

# Local modules
from src.bank import Bank
from src.utils import ErrorCode, setup_logger, setup_parser


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
        bad_args(_: None) -> tuple[int, str]: Function for commands with incorrect arguments.
        __check_args(args_number: int = 0, fn: callable = no_fn): Checks and sets the associated function based on the command.
        fn() -> tuple[int, str]: Executes the associated function and returns the result.

    Notes:
        This class represents a command in the banking application and is associated with specific functions.
        The associated function is determined based on the command string and the number of arguments.
    """

    def __init__(self, command: str, arguments: list, bank: Bank, logger: Logger):
        self.logger = logger
        self.command = command
        self.arguments = arguments
        self.__fn = self.no_fn

        match self.command:
            case "HI":
                self.__check_args(args_number=0, fn=self.hi)

            case "LOGIN":
                self.__check_args(args_number=2, fn=bank.login)

            case "REGISTER":
                self.__check_args(args_number=2, fn=bank.register)

            case "CHPASSWD":
                self.__check_args(args_number=3, fn=bank.change_password)

            case "BALANCE":
                self.__check_args(args_number=1, fn=bank.balance)

            case "DEPOSIT":
                self.__check_args(args_number=2, fn=bank.deposit)

            case "WITH":
                self.__check_args(args_number=2, fn=bank.withdraw)

            case "TRANSFER":
                self.__check_args(args_number=3, fn=bank.transfer)

            case "LOGOUT":
                self.__check_args(args_number=1, fn=bank.logout)

            #            case "PAY":
            #                self.__check_args(args_number=4, fn=bank.pay)

            case _:
                self.__arguments = []

    def no_fn(self, _=None) -> tuple[ErrorCode, str]:
        """
        Default function for non-valid commands.
        """
        return ErrorCode.UNKNOWN_COMMAND, ""

    def bad_args(self, _=None) -> tuple[ErrorCode, str]:
        """
        Default function for wrong number of arguments.
        """
        return ErrorCode.BAD_ARGUMENTS, ""

    def __check_args(self, args_number: int = 0, fn=no_fn):
        """
        Checks if the number of arguments supplied is correct.
        """
        if len(self.__arguments) != args_number:
            self.__arguments = []
            self.__fn = self.bad_args
        else:
            self.__fn = fn

    def hi(self, _=None) -> tuple[ErrorCode, str]:
        # TODO: Check if hostname identification can be done without this using the certificate
        """
        Function that handles first connection.
        """
        return ErrorCode.OK, "bank"

    def fn(self) -> tuple[ErrorCode, str]:
        """
        Executes the binded function of the command and returns the error code.
        """
        if self.fn != self.no_fn:
            self.logger.debug(
                f"{self.command}:{self.arguments} executed",
            )
        self.__error_code, data = self.__fn(*self.__arguments)
        if self.__error_code == ErrorCode.OK:
            return ErrorCode.OK, data
        return self.__error_code, ""


class BankTCPServer(ForkingTCPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler,
        bank: Bank,
        certfile: Path,
        keyfile: Path,
        verbose: bool,
    ):
        self.bank = bank
        self.certfile = certfile
        self.keyfile = keyfile
        self.verbose = verbose
        self.sessions = {}

        super().__init__(
            server_address,
            lambda *args, **kwargs: handler(*args, **kwargs),
        )
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class BankUDPServer(ForkingUDPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler,
        bank: Bank,
        certfile: Path,
        keyfile: Path,
        verbose: bool,
    ):
        self.bank = bank
        self.certfile = certfile
        self.keyfile = keyfile
        self.verbose = verbose

        super().__init__(
            server_address,
            lambda *args, **kwargs: handler(
                *args, **kwargs, certfile=self.certfile, keyfile=self.keyfile
            ),
        )
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class BankTCPServerHandler(StreamRequestHandler):
    def __init__(
        self,
        request,
        client_address,
        server: BankTCPServer,
        logger: Logger,
    ):
        self.logger = logger
        self.bank = server.bank
        self.sessions = server.sessions

        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=server.certfile, keyfile=server.keyfile)
        request = context.wrap_socket(server.socket, server_side=True)

        super().__init__(request, client_address, server)

    def check_user(self, connected_uuid: str, cmd_uuid: str) -> bool:
        return connected_uuid == cmd_uuid

    def handle_error(self, error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR):
        error_msg = f"Error {error_code.value}: {error_code}"
        self.logger.error(error_msg)
        self.request.sendall(f"ERR {error_code.value}\r\n".encode("utf-8"))

    def send_ok_data(self, ok_data=""):
        self.request.sendall(f"OK {ok_data}\r\n".encode("utf-8"))

    def handle_logout(self, client_address: str):
        # Removes sessions entry for current session and logs the event
        del self.sessions[client_address]
        self.logger.info(f"User {self.username} has logged out")

    def handle_pre_login(self, data: str) -> bool:
        # Initializes the logged_in flag
        logged_in = False

        # Extracts command and data from input
        command, *arguments = data.split()
        cmd = Command(
            bank=self.bank, command=command, arguments=arguments, logger=self.logger
        )
        self.logger.info(f"Command {command} issued by {self.client_address}")

        # Handle error
        error_code, cmd_return = cmd.fn()
        if error_code != ErrorCode.OK:
            self.handle_error(error_code)

        else:
            self.send_ok_data(cmd_return)
            if command == "LOGIN":
                # Updates sessions dictionary
                self.sessions[self.client_address] = cmd_return

                # Logs login event and changes the flag
                self.username = arguments[0]
                self.uuid = cmd_return
                self.logger.info(f"User {self.username} has logged in")
                logged_in = True

        return logged_in

    def handle_post_login(self, data: str) -> bool:
        # Extracts command and data from input
        command, *arguments = data.split()

        # Sets connected UUID as argument if not given by client
        if arguments == []:
            arguments = [self.uuid]

        cmd = Command(
            bank=self.bank, command=command, arguments=arguments, logger=self.logger
        )
        self.logger.info(
            f"Command {command} issued by {self.username}:{self.client_address}"
        )

        # Check that UUID argument is the same as the session UUID
        if command != "LOGIN":
            if not self.check_user(arguments[0], self.sessions[self.client_address]):
                error_code = ErrorCode.UNAUTHORIZED_ACCESS
                self.handle_error(error_code)
                return True

        # Handle error
        error_code, cmd_return = cmd.fn()
        if error_code != ErrorCode.OK:
            self.handle_error(error_code)
            return True
        else:
            self.send_ok_data(cmd_return)
            if command == "LOGOUT":
                self.handle_logout(self.client_address)
                return False
            return True

    def handle(self):
        self.logger.info(f"Accepted connection from {self.client_address}")
        logged = False

        while True:
            if not logged:
                # Read data from buffer
                data = self.request.recv(4096)

                # Check if client disconnected
                if not data:
                    self.logger.info(f"Finished connection from {self.client_address}")
                    break

                # Checks non-empty message
                if len(data) <= 2:
                    self.logger.warning("Empty message")
                    continue

                # Handle pre-login
                logged = self.handle_pre_login(data.decode("utf-8"))
            else:
                # Read data from buffer
                data = self.request.recv(4096)

                # Check if client disconnected
                if not data:
                    self.handle_logout(self.client_address)
                    self.logger.info(f"Finished connection from {self.client_address}")
                    break

                # Checks non-empty message
                if len(data) <= 2:
                    self.logger.warning("Empty message")
                    continue

                logged = self.handle_post_login(data.decode("utf-8"))

        self.finish()


class BankUDPServerHandler(DatagramRequestHandler):
    pass


#     def __init__(self, request, *args, **kwargs):
#         # Initialize storage
#         self.bank = Bank()
#         self.sessions = {}
#
#         # Create SSL context
#         context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#         context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
#
#         request = context.wrap_socket(request, server_side=True)
#
#         super().__init__(request, *args, **kwargs)
#
#     def handle_error(self, error_code: int):
#         error_msg = f"Error {error_code}: "
#         match error_code:
#             case 1:
#                 error_msg += "Invalid login"
#             case 2:
#                 error_msg += "Invalid registration"
#             case 3:
#                 error_msg += "Insufficient funds"
#             case 251:
#                 error_msg += "Unauthorized access"
#             case 252:
#                 error_msg += "UUID not found"
#             case 253:
#                 error_msg += "Bad arguments"
#             case 254:
#                 error_msg += "Unknown command"
#             case 255:
#                 error_msg += "Unknown error"
#
#         self.server.logger.error(error_msg)
#
#     def encrypt(self, msg: str, n: int):
#         result = ""
#         for char in msg:
#             if char.isalpha():
#                 # Shift letters
#                 if char.islower():
#                     result += chr((ord(char) - ord("a") + n) % 26 + ord("a"))
#                 else:
#                     result += chr((ord(char) - ord("A") + n) % 26 + ord("A"))
#             elif char.isdigit():
#                 # Shift numbers
#                 result += chr((ord(char) - ord("0") + n) % 10 + ord("0"))
#             else:
#                 # Keep spaces unchanged
#                 result += char
#         return result
#
#     def decrypt(self, msg: str, n: int) -> str:
#         return self.encrypt(msg, -n)
#
#     def send_encrypted_data(self, conn, to, n: int, encrypted_msg: str):
#         self.server.logger.debug(f"encrypted message: {encrypted_msg} {n}\r\n")
#         conn.sendto(f"{encrypted_msg} {n}\r\n".encode("utf-8"), to)
#
#     def send_error_code(self, conn, to: socket.socket, n: int, error_code: int = 255):
#         self.server.logger.debug(f"error_code: {error_code}")
#         self.send_encrypted_data(conn, to, n, self.encrypt(f"ERR {error_code}", n))
#
#     def send_ok_data(self, conn, to: socket.socket, n: int, ok_data: str = ""):
#         self.server.logger.debug(f"ok_data: {ok_data}")
#         self.send_encrypted_data(conn, to, n, self.encrypt(f"OK {ok_data}", n))
#
#     def handle(self):
#         # Log and get info about the connection
#         self.server.logger.info(f"Received UDP message from {self.client_address}")
#         data, conn = self.request
#
#         # Decode the data and decrypt it
#         decoded_data = data.decode("utf-8")
#         if len(decoded_data) <= 1:
#             self.server.logger.warning("Empty message")
#             self.finish()
#             return
#         n = decoded_data.split()[-1]
#
#         # Handle bad cypher decode number
#         if not n.isdigit():
#             self.server.logger.warning("Bad cypher")
#             self.finish()
#             return
#
#         # Decrypt using the decode number
#         decrypted_data = self.decrypt(decoded_data, int(n))
#         self.server.logger.debug(f"Decrypted data: {decrypted_data}")
#
#         # Generate random n for answer
#         rand_n = randint(1, 25)
#         self.server.logger.debug(f"N: {rand_n}")
#         # n = 0 means no encryption
#         # rand_n = 0
#
#         # Validate the only command accepted through UDP
#         if decrypted_data.startswith("PAY"):
#             # Extracts command and data from input
#             command, *arguments = decrypted_data.split()
#
#             # Exclude the decryption number
#             arguments = arguments[:-1]
#             cmd = Command(command, arguments)
#             cmd.debug()
#             self.server.logger.info(f"Command {command} issued by {self.client_address}")
#
#             # Handle any error and send error code to client
#             error_code, cmd_return = cmd.fn()
#             if error_code != 0:
#                 self.handle_error(error_code)
#                 self.send_error_code(conn, self.client_address, rand_n, error_code)
#                 self.finish()
#                 return
#             # If no error, send OK data
#             self.send_ok_data(conn, self.client_address, rand_n, cmd_return)
#         # If command is not PAY, send bad argument
#         else:
#             error_code = 253
#             self.send_error_code(conn, self.client_address, rand_n, error_code)
#         self.finish()


class Server:
    """
    Server object that handles communications.
    """

    def __init__(
        self,
        server_address: tuple[str, int],
        dbpath: Path,
        certfile: Path,
        keyfile: Path,
        verbose: bool = False,
    ):
        self.logger = setup_logger(name="server", verbose=verbose)
        self.server_address = server_address
        self.bank = Bank(dbpath, verbose)

        # Create servers and their threads
        self.udp_server = BankUDPServer(
            server_address=server_address,
            handler=BankUDPServerHandler,
            bank=self.bank,
            certfile=certfile,
            keyfile=keyfile,
            verbose=verbose,
        )

        self.tcp_server = BankTCPServer(
            server_address=server_address,
            handler=BankUDPServerHandler,
            bank=self.bank,
            certfile=certfile,
            keyfile=keyfile,
            verbose=verbose,
        )

        self.udp_thread = Thread(target=self.udp_server.serve_forever)
        self.tcp_thread = Thread(target=self.tcp_server.serve_forever)

    def start(self):
        # Start the threads
        ip, port = self.server_address
        self.udp_thread.start()
        self.logger.info(f"UDP Server listening on {ip}:{port}")
        self.tcp_thread.start()
        self.logger.info(f"TCP Server listening on {ip}:{port}")

        # Wait for both threads to finish
        self.tcp_thread.join()
        self.udp_thread.join()

    def stop(self):
        # Empty print to not have the ^C in the same line as the warn
        print("")
        self.logger.warning("Stopping server, please wait...")

        # Shutdown both servers
        SERVER.tcp_server.shutdown()
        SERVER.udp_server.shutdown()


if __name__ == "__main__":
    # Enable logger and parser
    ARGS = setup_parser(
        prog="TeleGodsBank",
        description="TeleGodsBank is a TCP and UDP server that handles and processes bank transactions.",
    )

    # Extract arguments (IP Address needs to be a string)
    SERVER_ADDRESS = str(ARGS.ip_address), ARGS.port
    DBPATH = ARGS.dbpath
    CERTFILE = ARGS.certfile
    KEYFILE = ARGS.keyfile
    VERBOSE = ARGS.verbose

    # Create server instance
    SERVER = Server(
        server_address=SERVER_ADDRESS,
        dbpath=DBPATH,
        certfile=CERTFILE,
        keyfile=KEYFILE,
        verbose=VERBOSE,
    )

    # Handle Ctrl+C
    try:
        SERVER.start()

    except KeyboardInterrupt:
        SERVER.stop()
