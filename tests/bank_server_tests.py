import unittest
import argon2
from src.db import User, UserDatabase
from src.bank import Bank


class TestBankDB(unittest.TestCase):
    """
    Tests the basic CRUD suite of functions.
    """

    def setUp(self):
        self.user_db = UserDatabase()
        self.user = User(
            "aaaa-aaaa-aaaa-aaaa",
            "test_user1",
            argon2.PasswordHasher().hash("password1"),
        )
        self.user_db.create(self.user)

    def test_user_creation_and_retrieval_by_uuid(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(uuid=self.user.get_data()[0])

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(retrieved_user.get_data(), self.user.get_data())

    def test_user_creation_and_retrieval_by_username(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(username=self.user.get_data()[1])

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(retrieved_user.get_data(), self.user.get_data())

    def test_user_retrieval_without_parameters(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read()

        self.assertIsNone(retrieved_user)

    def test_password_update(self):
        new_password = "new_password"
        self.user_db.update(uuid=self.user.get_data()[0], password=new_password)

        updated_user = self.user_db.read(self.user.get_data()[0])
        if updated_user is not None:
            self.assertTrue(
                argon2.PasswordHasher().verify(updated_user.get_data()[2], new_password)
            )

    def test_balance_update(self):
        # Update the user's balance, expected should be delta because initial is zero
        delta_balance = 200.0
        expected_balance = delta_balance
        self.user_db.update(uuid=self.user.get_data()[0], delta_balance=delta_balance)

        updated_user = self.user_db.read(self.user.get_data()[0])
        if updated_user is not None:
            self.assertEqual(updated_user.get_data()[3], expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        self.user_db.delete("aaaa-aaaa-aaaa-aaaa")


class TestBankAuth(unittest.TestCase):
    """
    Tests the Bank class authentication.
    """

    def setUp(self):
        self.database = UserDatabase()
        self.bank = Bank(self.database)
        self.users = [(f"test_user{i}", "password") for i in range(1, 2)]
        self.uuids = []
        for user in self.users:
            self.bank.register(*user)
            user_data = self.database.read(username=user[0])
            if user_data is not None:
                self.uuids.append(user_data.get_data()[0])

    def test_user_login_with_correct_password(self):
        login_error_code, _ = self.bank.login(*self.users[0])
        expected_error_code = 0
        self.assertEqual(login_error_code, expected_error_code)

    def test_user_login_with_incorrect_password(self):
        wrong_password_user = (
            self.users[0][0],
            "wrong_password",
        )
        login_error_code, _ = self.bank.login(*wrong_password_user)
        expected_error_code = 1
        self.assertEqual(login_error_code, expected_error_code)

    def test_change_password_correctly(self):
        pass

    def test_change_password_failure(self):
        pass

    def tearDown(self):
        # Clean up the database after tests
        for uuid in self.uuids:
            self.database.delete(uuid)


class TestBankTransactions(unittest.TestCase):
    """
    Tests the basic transactions related to the bank.
    """

    def setUp(self):
        self.database = UserDatabase()
        self.bank = Bank(self.database)
        self.users = [(f"test_user{i}", "password") for i in range(1, 3)]
        self.uuids = []
        for user in self.users:
            self.bank.register(*user)
            user_data = self.database.read(username=user[0])
            if user_data is not None:
                self.uuids.append(user_data.get_data()[0])

    def test_deposit(self):
        # Use test_user1
        uuid = self.uuids[0]

        # Deposit delta_balance to test_user1 and test error code
        delta_balance = 5000
        deposit_error_code, _ = self.bank.deposit(uuid=uuid, amount=delta_balance)

        # Error 0 is no error
        expected_error_code = 0
        self.assertEqual(deposit_error_code, expected_error_code)

        # Check if expected_balance matches delta balance, because initial is 0.0
        _, new_balance = self.bank.balance(uuid=uuid)
        expected_balance = delta_balance
        self.assertEqual(float(new_balance), expected_balance)

    def test_withdraw_with_enough_balance(self):
        # Use test_user1
        uuid = self.uuids[0]

        # Deposit enough funds
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid, amount=deposit_amount)

        # Check balance before withdraw
        _, old_balance = self.bank.balance(uuid=uuid)

        # Withdraw from account
        withdraw_amount = 3000
        withdrawal_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)

        # Error 0 is no error
        expected_error_code = 0
        self.assertEqual(withdrawal_error_code, expected_error_code)

        # Confirm new balance, and succesful withdrawal
        _, new_balance = self.bank.balance(uuid=uuid)
        expected_balance = float(old_balance) - withdraw_amount
        self.assertEqual(float(new_balance), expected_balance)

    def test_withdraw_with_not_enough_balance(self):
        # Use test_user1
        uuid = self.uuids[0]

        # Check balance before withdraw
        _, old_balance = self.bank.balance(uuid=uuid)

        # Withdraw from account
        withdraw_amount = 3000
        withdraw_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)

        # Error 3 is insufficient funds
        expected_error_code = 3
        self.assertEqual(withdraw_error_code, expected_error_code)

        # Confirm unaffected balance and unsuccesful withdrawal
        _, new_balance = self.bank.balance(uuid=uuid)
        expected_balance = old_balance
        self.assertEqual(new_balance, expected_balance)

    def test_withdraw_with_just_enough_balance(self):
        # Use test_user1
        uuid = self.uuids[0]

        # Deposit enough funds
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid, amount=deposit_amount)

        # Check balance before withdraw
        _, old_balance = self.bank.balance(uuid=uuid)

        # Withdraw from account
        withdraw_amount = 5000
        withdrawal_error_code, _ = self.bank.withdraw(uuid=uuid, amount=withdraw_amount)

        # Error 0 is no error
        expected_error_code = 0
        self.assertEqual(withdrawal_error_code, expected_error_code)

        # Confirm new balance, and succesful withdrawal
        _, new_balance = self.bank.balance(uuid=uuid)
        expected_balance = float(old_balance) - withdraw_amount
        self.assertEqual(float(new_balance), expected_balance)

    def test_transfer_to_existent_user(self):
        # Use test_user1 and test_user2
        uuid1, uuid2 = self.uuids

        # Deposit enough funds
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid1, amount=str(deposit_amount))

        # Check balance before transfer
        _, old_balance1 = self.bank.balance(uuid=uuid1)
        _, old_balance2 = self.bank.balance(uuid=uuid2)

        # Transfer from test_user5 to test_user6
        transfer_amount = deposit_amount
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, receiver_uuid=uuid2, amount=str(transfer_amount)
        )

        # Error 0 is no error
        expected_error_code = 0
        self.assertEqual(transfer_error_code, expected_error_code)

        # Confirm new balances, and succesful transfer
        _, new_balance1 = self.bank.balance(uuid=uuid1)
        _, new_balance2 = self.bank.balance(uuid=uuid2)
        expected_balance1 = float(old_balance1) - transfer_amount
        expected_balance2 = float(old_balance2) + transfer_amount

        self.assertEqual(float(new_balance1), expected_balance1)
        self.assertEqual(float(new_balance2), expected_balance2)

    def test_transfer_to_non_existent_user(self):
        # Use test_user1 and non_existent_user
        uuid1 = self.uuids[0]
        uuid2 = "this-is-clearly-not-a-valid-uuid"

        # Deposit enough funds
        deposit_amount = 5000
        self.bank.deposit(uuid=uuid1, amount=deposit_amount)

        # Check balance before transfer
        _, old_balance = self.bank.balance(uuid=uuid1)

        # Try to transfer from test_user7 to a non existent user
        transfer_amount = deposit_amount
        transfer_error_code, _ = self.bank.transfer(
            sender_uuid=uuid1, receiver_uuid=uuid2, amount=transfer_amount
        )

        # Error 252 is UUID not found
        expected_error_code = 252
        self.assertEqual(transfer_error_code, expected_error_code)

        # Confirm same balance, and unsuccesful transfer
        _, new_balance = self.bank.balance(uuid=uuid1)
        expected_balance = old_balance

        self.assertEqual(new_balance, expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        for uuid in self.uuids:
            self.database.delete(uuid)


if __name__ == "__main__":
    unittest.main()
