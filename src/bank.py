# Standard library modules
from pathlib import Path
from uuid import uuid4

# Third party modules
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Local modules
from src.db import User, UserDatabase
from src.utils import setup_logger, ErrorCode

# Globals
OK = ErrorCode.OK
INVALID_REGISTRATION = ErrorCode.INVALID_REGISTRATION
INVALID_LOGIN = ErrorCode.INVALID_LOGIN
SESSION_CONFLICT = ErrorCode.SESSION_CONFLICT
INSUFFICIENT_FUNDS = ErrorCode.INSUFFICIENT_FUNDS
INSUFFICIENT_STOCK = ErrorCode.INSUFFICIENT_STOCK
UUID_NOT_FOUND = ErrorCode.UUID_NOT_FOUND
BAD_ARGUMENTS = ErrorCode.BAD_ARGUMENTS
UNKNOWN_ERROR = ErrorCode.UNKNOWN_ERROR


class Bank:
    def __init__(self, dbpath: Path, verbose: bool = False):
        self.logger = setup_logger(name="bank", verbose=verbose)
        self.logger.debug("Instantiating new Bank")

        self.__database = UserDatabase(dbpath=dbpath, verbose=verbose)
        self.__connected_users = set()

    def get_db(self) -> UserDatabase:
        return self.__database

    def register(self, username: str = "", password: str = "") -> tuple[ErrorCode, str]:
        self.logger.debug(
            f"Registering new user with username = {username}, password = {password}"
        )

        # Check empty fields
        if username == "" or password == "":
            return BAD_ARGUMENTS, ""

        # User is already registered
        user_data = self.__database.read(username=username)
        if user_data is not None:
            return INVALID_REGISTRATION, ""

        # Perform registration
        self.__database.create(
            User(
                uuid=uuid4().hex,
                username=username,
                password=PasswordHasher().hash(password),
            )
        )
        return OK, ""

    def logout(self, uuid: str = "") -> tuple[ErrorCode, str]:
        self.logger.debug(f"Logging out user with uuid = {uuid}")

        # Check empty fields
        if uuid == "":
            return BAD_ARGUMENTS, ""

        # UUID not logged in
        if uuid not in self.__connected_users:
            return UUID_NOT_FOUND, ""

        self.__connected_users.remove(uuid)
        return OK, ""

    def login(self, username: str = "", password: str = "") -> tuple[ErrorCode, str]:
        self.logger.debug(
            f"Logging in user with username = {username} and password = {password}"
        )

        # Check empty fields
        if username == "" or password == "":
            return BAD_ARGUMENTS, ""

        # User is not registered
        user_data = self.__database.read(username=username)
        if user_data is None:
            return INVALID_LOGIN, ""

        # We need to use a try/except because argon2 raises
        # an exception when a verification fails
        try:
            hash = user_data.password
            PasswordHasher().verify(hash, password)

        except VerifyMismatchError:
            return INVALID_LOGIN, ""

        else:
            # Check if user is not already connected
            uuid = user_data.uuid
            if uuid in self.__connected_users:
                return SESSION_CONFLICT, ""

            self.__connected_users.add(uuid)
            return OK, uuid

    def change_password(
        self, uuid: str = "", old_password: str = "", new_password: str = ""
    ) -> tuple[ErrorCode, str]:
        self.logger.debug(
            f"Changing password for user with uuid = {uuid} and passwords = {old_password} {new_password}"
        )

        # Check empty fields
        if uuid == "" or old_password == "" or new_password == "":
            return BAD_ARGUMENTS, ""

        # User is not registered
        user_data = self.__database.read(uuid=uuid)
        if user_data is None:
            return UUID_NOT_FOUND, ""

        # Validate passwords
        login_error_code, _ = self.login(
            username=user_data.username, password=old_password
        )
        if login_error_code != 0:
            return login_error_code, ""

        self.__database.update(uuid=uuid, password=new_password)
        return OK, ""

    def balance(self, uuid: str = "") -> tuple[ErrorCode, str]:
        self.logger.debug(f"Checking balance for user with uuid = {uuid}")

        # Validate input
        if uuid == "":
            return BAD_ARGUMENTS, ""

        # User doesn't exists
        user_data = self.__database.read(uuid=uuid)
        if user_data is None:
            return UUID_NOT_FOUND, ""

        return OK, str(user_data.balance)

    def deposit(self, uuid: str = "", amount: str = "") -> tuple[ErrorCode, str]:
        self.logger.debug(
            f"Adding funds for user with uuid = {uuid} with amount = {amount}"
        )

        # Validate input
        if uuid == "" or amount == "":
            return BAD_ARGUMENTS, ""

        # Cast string input to float
        deposit_amount = float(amount)
        self.__database.update(uuid=uuid, delta_balance=deposit_amount)
        return OK, ""

    def withdraw(self, uuid: str = "", amount: str = "") -> tuple[ErrorCode, str]:
        """
        Withdraws money from a user's account.

        Args:
            uuid (str): The UUID of the user.
            amount (float): The amount to withdraw.

        Returns:
            tuple[ErrorCode, str]: A tuple containing the error code and additional information.
        """
        self.logger.debug(
            f"Withdrawing funds from user with uuid = {uuid} with amount = {amount}"
        )

        # Validate input
        if uuid == "" or amount == "":
            return BAD_ARGUMENTS, ""

        # Check funds
        error_code, balance = self.balance(uuid)
        if error_code != OK:
            return UUID_NOT_FOUND, ""

        balance = float(balance)
        withdraw_amount = float(amount)
        if balance - withdraw_amount < 0.0:
            return INSUFFICIENT_FUNDS, ""

        self.__database.update(uuid=uuid, delta_balance=-withdraw_amount)
        return OK, ""

    def transfer(
        self, sender_uuid: str = "", receiver_uuid: str = "", amount: str = ""
    ) -> tuple[ErrorCode, str]:
        """
        Transfers money from one user to another.

        Args:
            sender_uuid (str): The UUID of the sender.
            receiver_uuid (str): The UUID of the receiver.
            amount (float): The amount to transfer.

        Returns:
            tuple[ErrorCode, str]: A tuple containing the error code and additional information.
        """
        self.logger.debug(
            f"Transfering funds from user with uuid = {sender_uuid} to user with uuid = {receiver_uuid} with amount = {amount}"
        )

        # Validate input
        if sender_uuid == "" or receiver_uuid == "" or amount == "":
            return BAD_ARGUMENTS, ""

        # Verify that receiver account exists
        if self.__database.read(uuid=receiver_uuid) is None:
            return UUID_NOT_FOUND, ""

        # Check funds
        withdraw_error_code, _ = self.withdraw(uuid=sender_uuid, amount=amount)

        if withdraw_error_code == OK:
            return self.deposit(uuid=receiver_uuid, amount=amount)

        return withdraw_error_code, ""


#     def pay(
#         self,
#         sender_uuid: str = "",
#         receiver_uuid: str = "",
#         amount: str = "",
#         password: str = "",
#     ) -> tuple[int, str]:
#         """
#         Commits a payment, a transfer with included password
#
#         Args:
#             sender_uuid (str): The UUID of the sender.
#             receiver_uuid (str): The UUID of the receiver.
#             amount (str): The amount to transfer.
#             password (str): The password of the sender account.
#
#         Returns:
#             tuple[int, str]: A tuple containing the error code and additional information.
#
#         Notes:
#             Error codes:
#                 0: Success
#                 252: User not found in the database
#                 253: Invalid input
#         """
#         # Validate input
#         if sender_uuid == "" or receiver_uuid == "" or amount == "":
#             return 253, ""
#
#         # Verify that receiver account exists
#         if self.__database.read(uuid=receiver_uuid) is None:
#             return 252, ""
#
#         # Verify that sender account exists and its password is correct
#         user = self.__database.read(uuid=sender_uuid)
#         if user is None:
#             return 253, ""
#         username = user.get_data()[1]
#
#         login_error_code, _ = self.login(username, password)
#
#         if login_error_code != 0:
#             return login_error_code, ""
#
#         # Check funds
#         withdraw_error_code, _ = self.withdraw(uuid=sender_uuid, amount=amount)
#
#         if withdraw_error_code == 0:
#             return self.deposit(uuid=receiver_uuid, amount=amount)
#
#         return withdraw_error_code, ""
