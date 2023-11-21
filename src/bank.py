from src.db import User, UserDatabase
from dataclasses import dataclass
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Bank:
    def __init__(self, database: UserDatabase = UserDatabase()):
        self.__database = database

    def register(self, username: str, password: str) -> bool:
        username_free = self.__database.read(username=username) is None

        if not username_free:
            return False

        self.__database.create(
            User(str(uuid4()), username, PasswordHasher().hash(password))
        )
        return True

    def login(self, username: str, password: str) -> bool:
        user_data = self.__database.read(username=username)
        # User doesn't exists
        if user_data is None:
            return False
        # We need to use a try/except because argon2 raises
        # exceptions when a verification fails
        try:
            PasswordHasher().verify(user_data.get_data()[2], password)
            return True
        except VerifyMismatchError:
            return False

    def change_password(self, uuid: str, old_password: str, new_password: str) -> bool:
        return True

    def balance(self, uuid: str) -> float:
        user_data = self.__database.read(uuid)
        if user_data is None:
            return 0.0
        return user_data.get_data()[3]

    def deposit(self, uuid: str, amount: float):
        self.__database.update(uuid, delta_balance=amount)

    def withdraw(self, uuid: str, amount: float) -> bool:
        balance = self.balance(uuid)
        if balance - amount < 0.0:
            return False
        self.__database.update(uuid=uuid, delta_balance=-amount)
        return True

    def transfer(self, sender_uuid: str, receiver_uuid: str, amount: float) -> bool:
        # Verify that receiver account exists
        if self.__database.read(uuid=receiver_uuid) is None:
            return False

        # Verify enough funds in sender account
        if self.withdraw(uuid=sender_uuid, amount=amount):
            self.deposit(uuid=receiver_uuid, amount=amount)
            return True
        return False
