# Standard library modules
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Third party modules
from argon2 import PasswordHasher

# Local modules
from src.utils import setup_logger


@dataclass
class User:
    """
    Represents a user in the bank with a unique identifier (UUID),
    a username, a hashed password, and a balance.

    Attributes:
        uuid (str): A unique identifier (UUID) for the user.
        username (str): The username associated with the user.
        password (str): The hashed password of the user.
        balance (float): The balance associated with the user.
    """

    uuid: str
    username: str
    password: str
    balance: float = 0.0

    def get_data(self) -> tuple[str, str, str, float]:
        """
        Retrieves all the User data as a tuple containing each attribute.

        Returns:
            tuple[str, str, str, float]: A tuple containing User data.
        """
        return self.uuid, self.username, self.password, self.balance


class UserDatabase:
    """
    A class representing a user database with methods to interact with user data.

    Attributes:
        dbpath (str): The path to the SQLite database file.

    Methods:
        create(user: User): Inserts a new user into the database.
        read(uuid: str): Reads an existing user from the database.
        update(uuid: str, password: str, delta_balance: float): Updates a password and/or adds to the balance of an existing user.
        delete(uuid: str): Removes an existing user from the database.
    """

    def __init__(self, dbpath: Path, verbose: bool = False):
        """
        Initializes the database with a standard bank table containing the
        User data.

        Args:
            dbpath (str): The path to the DB.
        """
        self.__logger = setup_logger(name="db", verbose=verbose)
        self.__logger.debug(f"Instantiating new UserDatabase with dbpath = {dbpath}")

        self.__dbpath = dbpath

        # Create directories if they don't exist
        if not self.__dbpath.is_file():
            self.__logger.debug("Creating database file")
            self.__dbpath.parent.mkdir(parents=True, exist_ok=True)

        # Create table if it doesn't exists
        with sqlite3.connect(self.__dbpath) as connection:
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
        self.__logger.info("Database succesfully loaded.")

    def create(self, user: User):
        """
        Inserts a new user into the 'bank' table of the database.

        Args:
            user (User): The User instance to be inserted into the database.
        """
        self.__logger.debug(f"Creating user with data = {user.get_data()}")

        with sqlite3.connect(self.__dbpath) as connection:
            connection.execute(
                """
                    INSERT INTO bank (uuid, username, hash, balance)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(username) DO NOTHING;
                """,
                user.get_data(),
            )

    def read(self, uuid: str = "", username: str = "") -> User | None:
        """
        Retrieves a user from the 'bank' table by UUID.

        Args:
            uuid (str): The UUID of the user to be retrieved.

        Returns:
            User | None: A User instance if found, or None if the user is not found.
        """
        search_keyword = "uuid" if uuid != "" else "username"
        search_value = uuid if search_keyword == "uuid" else username
        self.__logger.debug(f"Reading user with {search_keyword} = {search_value}")

        with sqlite3.connect(self.__dbpath) as connection:
            cursor = connection.cursor()
            query = f"SELECT * FROM bank WHERE {search_keyword} = ?"
            result = cursor.execute(
                query,
                (search_value,),
            )
            user = result.fetchone()
            self.__logger.debug(f"Got {user if user is not None else 'nothing'}")

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
            At least one parameter between 'password' and 'delta_balance' has to be provided,
            If both 'password' and 'delta_balance' are provided, the function updates both
        """

        def __update_password(uuid: str, password: str):
            """
            Updates the password for a user in the 'bank' table.

            Args:
                uuid (str): The UUID of the user.
                password (str): The new password for the user.
            """
            self.__logger.debug(
                f"Updating password for uuid = {uuid}, using password = {password}"
            )

            with sqlite3.connect(self.__dbpath) as connection:
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
            self.__logger.debug(
                f"Updating balance for uuid = {uuid}, using delta_balance = {delta_balance}"
            )

            with sqlite3.connect(self.__dbpath) as connection:
                user = self.read(uuid=uuid)
                if user is None:
                    raise NameError(f"User with UUID {uuid} not found.")
                current_balance = user.balance
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
        """
        Deletes a user from the 'bank' table based on the provided UUID.

        Args:
            uuid (str): The UUID of the user to be deleted.
        """
        self.__logger.debug(f"Deleting user with uuid = {uuid}")

        with sqlite3.connect(self.__dbpath) as connection:
            connection.execute(
                """
                    DELETE FROM bank 
                    WHERE uuid = ?;
                """,
                (uuid,),
            )
