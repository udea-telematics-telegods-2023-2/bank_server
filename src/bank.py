from src.db import User, UserDatabase
from dataclasses import dataclass
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


@dataclass
class UserDT:
    username: str
    password: str


class Bank:
    def __init__(self, database: UserDatabase):
        self.__database = database

    def register(self, user: UserDT) -> bool:
        username_free = self.__database.read(username=user.username) is None

        if not username_free:
            return False

        self.__database.create(
            User(str(uuid4()), user.username, PasswordHasher().hash(user.password))
        )
        return True

    def login(self, user: UserDT) -> bool:
        user_data = self.__database.read(username=user.username)
        # User doesn't exists
        if user_data is None:
            return False
        # We need to use a try/except because argon2 raises exceptions when
        # a verification fails
        try:
            PasswordHasher().verify(user_data.get_data()[2], user.password)
            # Password matches the hash
            return True
        except VerifyMismatchError:
            return False
