from os import makedirs
import sqlite3
from argon2 import PasswordHasher
from dataclasses import dataclass

# Import utils
from src.utils import get_project_root

PROJECT_ROOT = get_project_root()


@dataclass
class User:
    """
    Represents a user in the bank with a unique identifier (UUID),
    a username, a hashed password, and a balance.

    Attributes:
        uuid (str): A unique identifier (UUID) for the user.
        username (str): The username associated with the user.
        hash (str): The hashed password of the user.
        balance (float): The balance associated with the user.

    Methods:
        get_data() -> tuple[str, str, str, float]:
            Retrieves the user data as a tuple containing UUID, username, hashed password, and balance.
    """

    uuid: str
    username: str
    hashed_password: str
    balance: float = 0.0

    def get_data(self) -> tuple[str, str, str, float]:
        """
        Retrieves the User data as a tuple containing UUID, username, hashed password, and balance.

        Returns:
            tuple[str, str, str, float]: A tuple containing User data.
        """
        return self.uuid, self.username, self.hashed_password, self.balance


class UserDatabase:
    """
    A class representing a user database with methods to interact with user data.

    Attributes:
        db_path (str): The path to the SQLite database file.

    Methods:
        create(user: User): Inserts a new user into the database.
        read(uuid: str): Reads an existing user from the database.
        update(uuid: str, password: str, delta_balance: float): Updates a password or adds to the balance of an existing user.
        delete(uuid: str): Removes an existing user from the database.

    Note:
        This class assumes the existence of a 'bank' table in the database with columns
        'uuid', 'username', 'hash', and 'balance'.
    """

    def __init__(self, db_path: str = f"{PROJECT_ROOT}/db/bank.db"):
        """
        Initializes the database with a standard bank table containing the
        User data.

        Args:
            db_path (str): The path to the DB, defaults to {PROJECT_ROOT}/db/bank.db
        """
        self.__db_path: str = db_path
        # Create directories if they don't exist
        makedirs(db_path[: db_path.rindex("/")], exist_ok=True)
        with sqlite3.connect(self.__db_path) as connection:
            connection.execute(
                """
                        CREATE TABLE IF NOT EXISTS bank (
                            uuid TEXT PRIMARY KEY,
                            username TEXT UNIQUE,
                            hash TEXT,
                            balance REAL
                        );
                    """
            )

    def create(self, user: User):
        """
        Inserts a new user into the 'bank' table of the database.

        Args:
            user (User): The User instance to be inserted into the database.
        """
        with sqlite3.connect(self.__db_path) as connection:
            connection.execute(
                """
                    INSERT INTO bank (uuid, username, hash, balance)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(username) DO NOTHING;
                """,
                user.get_data(),
            )

    def read(self, uuid: str | None = None, username: str | None = None) -> User | None:
        """
        Retrieves a user from the 'bank' table by UUID.

        Args:
            uuid (str): The UUID of the user to be retrieved.

        Returns:
            User | None: A User instance if found, or None if the user is not found.
        """
        if uuid is None and username is None:
            return None

        with sqlite3.connect(self.__db_path) as connection:
            cursor = connection.cursor()
            query = f"SELECT * FROM bank WHERE {'uuid' if uuid is not None else 'username'} = ?"
            result = cursor.execute(
                query,
                (uuid if uuid is not None else username,),
            )
            user = result.fetchone()
            return User(*user) if user is not None else user

    def update(self, uuid: str, password: str = "", delta_balance: float = 0.0):
        """
        Updates user information in the 'bank' table.

        Args:
            uuid (str): The UUID of the user to be updated.
            password (str, optional): The new password for the user. Defaults to an empty string.
            delta_balance (float, optional): The change in balance for the user. Defaults to 0.0.

        Raises:
            NameError: If the user with the specified UUID is not found.

        Note:
            If both 'password' and 'delta_balance' are provided, the function updates both.
        """

        def __update_password(uuid: str, password: str):
            """
            Updates the password for a user in the 'bank' table.

            Args:
                uuid (str): The UUID of the user.
                password (str): The new password for the user.
            """
            with sqlite3.connect(self.__db_path) as connection:
                connection.execute(
                    """
                        UPDATE bank
                        SET hash = ?
                        WHERE uuid = ?
                    """,
                    (PasswordHasher().hash(password), uuid),
                )

        def __update_balance(uuid: str, delta_balance: float):
            """
            Updates the balance for a user in the 'bank' table.

            Args:
                uuid (str): The UUID of the user.
                delta_balance (float): The change in balance for the user.
            """
            with sqlite3.connect(self.__db_path) as connection:
                user = self.read(uuid)
                if user is None:
                    raise NameError(f"User with UUID {uuid} not found.")
                current_balance = user.get_data()[3]
                new_balance = current_balance + delta_balance
                connection.execute(
                    """
                        UPDATE bank
                        SET balance = ?
                        WHERE uuid = ?
                    """,
                    (new_balance, uuid),
                )

        if password != "":
            __update_password(uuid, password)

        if delta_balance != 0.0:
            __update_balance(uuid, delta_balance)

    def delete(self, uuid: str):
        with sqlite3.connect(self.__db_path) as connection:
            connection.execute(
                """
                    DELETE FROM bank 
                    WHERE uuid = ?;
                """,
                (uuid,),
            )
