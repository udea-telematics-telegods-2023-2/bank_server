from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.db import User, UserDatabase
from uuid import uuid4


class Bank:
    """
    Represents a simple banking system with user registration, login, and basic transaction functionalities.

    Attributes:
        database (UserDatabase): The database to store user information.
    """

    def __init__(self, database: UserDatabase = UserDatabase()):
        """
        Initializes a new instance of the Bank class.

        Args:
            database (UserDatabase): The database to store user information.
        """
        self.__database = database

    def register(self, username: str = "", password: str = "") -> tuple[int, str]:
        """
        Registers a new user in the system.

        Args:
            username (str): The username for the new user.
            password (str): The plain-text password for the new user.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                2: Username already taken
                253: Invalid input
        """
        # Validate input
        if username == "" or password == "":
            return 253, ""

        # Validate free username
        username_free = self.__database.read(username=username) is None
        if not username_free:
            return 2, ""

        self.__database.create(
            User(str(uuid4()), username, PasswordHasher().hash(password))
        )
        return 0, ""

    def login(self, username: str = "", password: str = "") -> tuple[int, str]:
        """
        Logs in an existing user.

        Args:
            username (str): The username of the user trying to log in.
            password (str): The plain-text password of the user.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                1: User doesn't exist
                253: Invalid input
        """
        # Validate input
        if username == "" or password == "":
            return 253, ""

        # User doesn't exists
        user_data = self.__database.read(username=username)
        if user_data is None:
            return 1, ""

        # We need to use a try/except because argon2 raises
        # exceptions when a verification fails
        try:
            hash = user_data.get_data()[2]
            PasswordHasher().verify(hash, password)
            uuid = user_data.get_data()[0]
            return 0, uuid
        except VerifyMismatchError:
            return 1, ""

    def logout(self) -> tuple[int, str]:
        """
        Logs out the current user.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
        """
        return 0, ""

    def change_password(
        self, uuid: str = "", old_password: str = "", new_password: str = ""
    ) -> tuple[int, str]:
        """
        Changes the password for a user.

        Args:
            uuid (str): The UUID of the user.
            old_password (str): The old plain-text password.
            new_password (str): The new plain-text password.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                252: User not found in the database
                253: Old password doesn't match new password
        """
        # User doesn't exists
        user_data = self.__database.read(uuid)
        if user_data is None:
            return 252, ""

        # Validate passwords
        login_error_code, _ = self.login(user_data.get_data()[1], old_password)
        if login_error_code != 0:
            return login_error_code, ""

        self.__database.update(uuid, new_password)
        return 0, ""

    def balance(self, uuid: str = "") -> tuple[int, str]:
        """
        Retrieves the balance for a user.

        Args:
            uuid (str): The UUID of the user.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                252: User not found in the database
                253: Invalid input
        """
        # Validate input
        if uuid == "":
            return 253, ""

        # User doesn't exists
        user_data = self.__database.read(uuid)
        if user_data is None:
            return 252, ""

        return 0, str(user_data.get_data()[3])

    def deposit(self, uuid: str = "", amount: str = "") -> tuple[int, str]:
        """
        Deposits money into a user's account.

        Args:
            uuid (str): The UUID of the user.
            amount (str): The amount to deposit.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                252: User not found in the database
                253: Invalid input
        """
        # Validate input
        if uuid == "" or amount == "":
            return 253, ""

        self.__database.update(uuid, delta_balance=float(amount))
        return 0, ""

    def withdraw(self, uuid: str = "", amount: str = "") -> tuple[int, str]:
        """
        Withdraws money from a user's account.

        Args:
            uuid (str): The UUID of the user.
            amount (str): The amount to withdraw.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                3: Insufficient funds
                253: Invalid input
        """
        # Validate input
        if uuid == "" or amount == "":
            return 253, ""

        # Check funds
        balance = float(self.balance(uuid)[1])
        if balance - float(amount) < 0.0:
            return 3, ""

        self.__database.update(uuid=uuid, delta_balance=-float(amount))
        return 0, ""

    def transfer(
        self, sender_uuid: str = "", receiver_uuid: str = "", amount: str = ""
    ) -> tuple[int, str]:
        """
        Transfers money from one user to another.

        Args:
            sender_uuid (str): The UUID of the sender.
            receiver_uuid (str): The UUID of the receiver.
            amount (str): The amount to transfer.

        Returns:
            tuple[int, str]: A tuple containing the error code and additional information.

        Notes:
            Error codes:
                0: Success
                252: User not found in the database
                253: Invalid input
        """
        # Validate input
        if sender_uuid == "" or receiver_uuid == "" or amount == "":
            return 253, ""

        # Verify that receiver account exists
        if self.__database.read(uuid=receiver_uuid) is None:
            return 252, ""

        # Check funds
        withdraw_error_code, _ = self.withdraw(uuid=sender_uuid, amount=amount)

        if withdraw_error_code == 0:
            return self.deposit(uuid=receiver_uuid, amount=amount)

        return withdraw_error_code, ""
