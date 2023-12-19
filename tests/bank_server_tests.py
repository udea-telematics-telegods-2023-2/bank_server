# Standard library modules
import asyncio
import socket
import ssl
import unittest

from os import remove
from pathlib import Path

# Third party modules
import argon2

# Local modules
from src.bank import Bank
from src.db import User, UserDatabase
from src.server import Server
from src.utils import ErrorCode

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


class TestDB(unittest.TestCase):
    """
    Tests the basic CRUD suite of functions.
    """

    def setUp(self):
        self.path = Path("test.db")
        self.user_db = UserDatabase(self.path)
        self.user = User(
            uuid="aaaa-aaaa-aaaa-aaaa",
            username="test_user1",
            password=argon2.PasswordHasher().hash("password1"),
            balance=0.0,
        )
        self.user_db.create(self.user)

    def test_user_creation_and_retrieval_by_uuid(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(uuid=self.user.uuid)

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(retrieved_user.get_data(), self.user.get_data())

    def test_user_creation_and_retrieval_by_username(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(username=self.user.username)

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(retrieved_user.get_data(), self.user.get_data())

    def test_user_retrieval_without_parameters(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read()

        self.assertIsNone(retrieved_user)

    def test_nonexistent_user_retrieval_by_uuid(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(uuid="xxxx-xxxx-xxxx-xxxx")

        self.assertIsNone(retrieved_user)

    def test_nonexistent_user_retrieval_by_username(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(username="null")

        self.assertIsNone(retrieved_user)

    def test_password_update(self):
        new_password = "new_password"
        self.user_db.update(uuid=self.user.uuid, password=new_password)

        updated_user = self.user_db.read(uuid=self.user.uuid)
        if updated_user is not None:
            self.assertTrue(
                argon2.PasswordHasher().verify(updated_user.password, new_password)
            )

    def test_balance_update(self):
        # Update the user's balance, expected should be delta because initial is zero
        delta_balance = 200.0
        expected_balance = delta_balance

        self.user_db.update(uuid=self.user.uuid, delta_balance=delta_balance)

        updated_user = self.user_db.read(uuid=self.user.uuid)
        if updated_user is not None:
            self.assertEqual(updated_user.balance, expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        self.user_db.delete("aaaa-aaaa-aaaa-aaaa")
        remove(self.path)


class TestBankAuth(unittest.TestCase):
    """
    Tests the Bank class authentication.
    """

    def setUp(self):
        self.path = Path("test.db")
        self.bank = Bank(self.path)
        self.database = self.bank.get_db()
        self.users = [(f"test_user{i}", "password") for i in range(1, 2)]
        self.uuids = []
        for user in self.users:
            self.bank.register(*user)
            user_data = self.database.read(username=user[0])
            if user_data is not None:
                self.uuids.append(user_data.uuid)

    # Registration
    def test_user_registration_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        # Without username
        registration_error_code, _ = self.bank.register(password="password")
        self.assertEqual(registration_error_code, expected_error_code)

        # Without password
        registration_error_code, _ = self.bank.register(username="username")
        self.assertEqual(registration_error_code, expected_error_code)

    def test_user_registration_with_existent_user(self):
        expected_error_code = INVALID_REGISTRATION

        registration_error_code, _ = self.bank.register(*self.users[0])
        self.assertEqual(registration_error_code, expected_error_code)

    # Logout
    def test_user_logout_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        logout_error_code, _ = self.bank.logout()
        self.assertEqual(logout_error_code, expected_error_code)

    def test_user_logout_without_being_logged_in(self):
        expected_error_code = UUID_NOT_FOUND

        logout_error_code, _ = self.bank.logout(uuid="xxxx-xxxx-xxxx-xxxx")
        self.assertEqual(logout_error_code, expected_error_code)

    def test_user_logout(self):
        expected_error_code = OK

        _, uuid = self.bank.login(*self.users[0])
        logout_error_code, _ = self.bank.logout(uuid=uuid)
        self.assertEqual(logout_error_code, expected_error_code)

    # Login
    def test_user_login_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        # Without username
        login_error_code, _ = self.bank.login(password=self.users[0][1])
        self.assertEqual(login_error_code, expected_error_code)

        # Without password
        login_error_code, _ = self.bank.login(username=self.users[0][0])
        self.assertEqual(login_error_code, expected_error_code)

    def test_user_login_with_invalid_login(self):
        expected_error_code = INVALID_LOGIN

        non_existent_user = ("i_dont_exist", "password")
        login_error_code, _ = self.bank.login(*non_existent_user)
        self.assertEqual(login_error_code, expected_error_code)

        wrong_password_user = (
            self.users[0][0],
            "wrong_password",
        )
        login_error_code, _ = self.bank.login(*wrong_password_user)
        self.assertEqual(login_error_code, expected_error_code)

    def test_user_login_already_logged_in(self):
        expected_error_code = SESSION_CONFLICT

        # Login an user
        _, _ = self.bank.login(*self.users[0])

        login_error_code, _ = self.bank.login(*self.users[0])
        self.assertEqual(login_error_code, expected_error_code)

    def test_user_login_with_correct_password(self):
        expected_error_code = OK

        login_error_code, _ = self.bank.login(*self.users[0])
        self.assertEqual(login_error_code, expected_error_code)

    # Change password
    def test_change_password_correctly(self):
        pass

    def test_change_password_failure(self):
        pass

    def tearDown(self):
        # Clean up the database after tests
        for uuid in self.uuids:
            self.database.delete(uuid)
        remove(self.path)


class TestBankTransactions(unittest.TestCase):
    """
    Tests the basic transactions related to the bank.
    """

    def setUp(self):
        self.path = Path("test.db")
        self.bank = Bank(self.path)
        self.database = self.bank.get_db()
        self.users = [(f"test_user{i}", "password") for i in range(1, 3)]
        self.uuids = []
        for user in self.users:
            self.bank.register(*user)
            user_data = self.database.read(username=user[0])
            if user_data is not None:
                self.uuids.append(user_data.uuid)

    # Balance
    def test_balance_with_bad_arguments(self):
        expected_error_code = BAD_ARGUMENTS

        balance_error_code, _ = self.bank.balance()
        self.assertEqual(balance_error_code, expected_error_code)

    def test_balance_with_bad_uuid(self):
        expected_error_code = UUID_NOT_FOUND

        uuid = "xxxx-xxxx-xxxx-xxxx"
        balance_error_code, _ = self.bank.balance(uuid=uuid)
        self.assertEqual(balance_error_code, expected_error_code)

    def test_balance(self):
        expected_error_code = OK

        uuid = self.uuids[0]
        balance_error_code, _ = self.bank.balance(uuid=uuid)
        self.assertEqual(balance_error_code, expected_error_code)

    # Deposit
    def test_deposit_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        # Without UUID
        delta_balance = 5000
        deposit_error_code, _ = self.bank.deposit(amount=delta_balance)
        self.assertEqual(deposit_error_code, expected_error_code)

        # Without amount
        uuid = self.uuids[0]
        deposit_error_code, _ = self.bank.deposit(uuid=uuid)
        self.assertEqual(deposit_error_code, expected_error_code)

    def test_deposit(self):
        expected_error_code = OK

        # Use test_user1
        uuid = self.uuids[0]

        # Deposit delta_balance to test_user1 and test error code
        delta_balance = 5000
        deposit_error_code, _ = self.bank.deposit(uuid=uuid, amount=delta_balance)

        # Error 0 is no error
        self.assertEqual(deposit_error_code, expected_error_code)

        # Check if expected_balance matches delta balance, because initial is 0.0
        new_balance = float(self.bank.balance(uuid=uuid)[1])
        expected_balance = delta_balance
        self.assertEqual(new_balance, expected_balance)

    # Withdraw
    def test_withdraw_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        # Without UUID
        withdraw_amount = 3000
        withdrawal_error_code, _ = self.bank.withdraw(amount=withdraw_amount)
        self.assertEqual(withdrawal_error_code, expected_error_code)

        # Without amount
        uuid = self.uuids[0]
        withdrawal_error_code, _ = self.bank.withdraw(uuid=uuid)
        self.assertEqual(withdrawal_error_code, expected_error_code)

        # With negative amount
        uuid = self.uuids[0]
        withdraw_amount = -3000
        withdraw_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)
        self.assertEqual(withdraw_error_code, expected_error_code)

    def test_withdraw_with_not_enough_balance(self):
        expected_error_code = INSUFFICIENT_FUNDS

        uuid = self.uuids[0]
        _, old_balance = self.bank.balance(uuid=uuid)

        # Withdraw from account
        withdraw_amount = 3000
        withdraw_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)
        self.assertEqual(withdraw_error_code, expected_error_code)

        # Confirm unaffected balance and unsuccesful withdrawal
        expected_balance = old_balance
        _, new_balance = self.bank.balance(uuid=uuid)
        self.assertEqual(new_balance, expected_balance)

    def test_withdraw_with_enough_balance(self):
        expected_error_code = OK

        uuid = self.uuids[0]
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid, amount=deposit_amount)
        old_balance = float(self.bank.balance(uuid=uuid)[1])

        # Withdraw from account
        withdraw_amount = 3000
        withdraw_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)
        self.assertEqual(withdraw_error_code, expected_error_code)

        # Confirm new balance, and succesful withdrawal
        expected_balance = old_balance - withdraw_amount
        new_balance = float(self.bank.balance(uuid=uuid)[1])
        self.assertEqual(new_balance, expected_balance)

    # Transfer
    def test_transfer_with_bad_args(self):
        expected_error_code = BAD_ARGUMENTS

        uuid1, uuid2 = self.uuids
        transfer_amount = 5000

        # Without sender_uuid
        transfer_error_code, _ = self.bank.transfer(
            receiver_uuid=uuid2, amount=transfer_amount
        )
        self.assertEqual(transfer_error_code, expected_error_code)

        # Without receiver_uuid
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, amount=transfer_amount
        )
        self.assertEqual(transfer_error_code, expected_error_code)

        # Without amount
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, receiver_uuid=uuid2
        )
        self.assertEqual(transfer_error_code, expected_error_code)

    def test_transfer_to_and_from_non_existent_user(self):
        expected_error_code = UUID_NOT_FOUND

        uuid1 = self.uuids[0]
        uuid2 = "this-is-clearly-not-a-valid-uuid"
        transfer_amount = 5000

        # Sender UUID non existent
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid2, receiver_uuid=uuid1, amount=transfer_amount
        )
        self.assertEqual(transfer_error_code, expected_error_code)

        # Receiver UUID non existent
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, receiver_uuid=uuid2, amount=transfer_amount
        )
        self.assertEqual(transfer_error_code, expected_error_code)

    def test_transfer_to_existent_user(self):
        expected_error_code = OK

        uuid1, uuid2 = self.uuids
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid1, amount=deposit_amount)

        # Check balance before transfer
        old_balance1 = float(self.bank.balance(uuid=uuid1)[1])
        old_balance2 = float(self.bank.balance(uuid=uuid2)[1])

        transfer_amount = deposit_amount
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, receiver_uuid=uuid2, amount=transfer_amount
        )
        self.assertEqual(transfer_error_code, expected_error_code)

        # Confirm new balances, and succesful transfer
        new_balance1 = float(self.bank.balance(uuid=uuid1)[1])
        new_balance2 = float(self.bank.balance(uuid=uuid2)[1])
        expected_balance1 = old_balance1 - transfer_amount
        expected_balance2 = old_balance2 + transfer_amount

        self.assertEqual(new_balance1, expected_balance1)
        self.assertEqual(new_balance2, expected_balance2)

    def tearDown(self):
        # Clean up the database after tests
        for uuid in self.uuids:
            self.database.delete(uuid)

    # class TestServer(unittest.TestCase):
    #     """
    #     Tests the bank server.
    #     """
    #
    #     def setUp(self):
    #         self.server_address = ("localhost", 55555)
    #         self.server = Server(
    #             server_address=self.server_address,
    #             dbpath=Path("tests/test.db"),
    #             certfile=Path("tests/test.crt"),
    #             keyfile=Path("tests/test.key"),
    #             verbose=True,
    #         )
    #
    #         self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    #         self.context.load_verify_locations("tests/test.crt")
    #         self.server.tcp_thread.start()
    #
    #     async def test_client_ssl_connection(self):
    #         expected_response = "OK bank"
    #         message = "HI"
    #         with socket.create_connection(self.server_address) as sock:
    #             with self.context.wrap_socket(
    #                 sock, server_hostname=self.server_address[0]
    #             ) as ssock:
    #                 ssock.send(message.encode("utf-8"))
    #                 res = ssock.recv(2048).decode()
    #                 self.assertEqual(res, expected_response)
    #
    #     def tearDown(self):
    #         self.server.tcp_server.shutdown()
    #         self.server.tcp_thread.join()


if __name__ == "__main__":
    unittest.main()
