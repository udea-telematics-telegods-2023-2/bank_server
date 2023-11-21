from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.db import User, UserDatabase
from uuid import uuid4


class Bank:
    def __init__(self, database: UserDatabase = UserDatabase()):
        self.__database = database

    def register(self, username: str = "", password: str = "") -> tuple[int, str]:
        # Validate input
        if username == "" or password == "":
            return 255, ""

        # Validate free username
        username_free = self.__database.read(username=username) is None
        if not username_free:
            return 2, ""

        # Execute DB operation
        self.__database.create(
            User(str(uuid4()), username, PasswordHasher().hash(password))
        )
        return 0, ""

    def login(self, username: str = "", password: str = "") -> tuple[int, str]:
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

    def change_password(self, uuid: str, old_password: str, new_password: str) -> bool:
        return True

    def balance(self, uuid: str) -> tuple[int, str]:
        user_data = self.__database.read(uuid)
        if user_data is None:
            return False, str(0.0)
        return True, str(user_data.get_data()[3])

    def deposit(self, uuid: str, amount: float) -> tuple[int, str]:
        self.__database.update(uuid, delta_balance=amount)
        return 0, ""

    def withdraw(self, uuid: str, amount: float) -> tuple[int, str]:
        balance = float(self.balance(uuid)[1])
        if balance - amount < 0.0:
            return 3, ""
        self.__database.update(uuid=uuid, delta_balance=-amount)
        return 0, ""

    def transfer(
        self, sender_uuid: str, receiver_uuid: str, amount: float
    ) -> tuple[int, str]:
        # Verify that receiver account exists
        if self.__database.read(uuid=receiver_uuid) is None:
            return 252, ""

        # Verify enough funds in sender account
        withdraw_error_code, _ = self.withdraw(uuid=sender_uuid, amount=amount)
        if withdraw_error_code == 0:
            return self.deposit(uuid=receiver_uuid, amount=amount)
        return withdraw_error_code, ""
