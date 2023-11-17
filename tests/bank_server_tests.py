import unittest
import argon2
from src.db import User, UserDatabase
from src.bank import UserDT, Bank


class TestBankDB(unittest.TestCase):
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
            self.assertEqual(self.user.get_data(), retrieved_user.get_data())

    def test_user_creation_and_retrieval_by_username(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read(username=self.user.get_data()[1])

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(self.user.get_data(), retrieved_user.get_data())

    def test_user_retrieval_without_parameters(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read()

        self.assertIsNone(retrieved_user)

    def test_password_update(self):
        user = User(
            "bbbb-bbbb-bbbb-bbbb",
            "test_user2",
            argon2.PasswordHasher().hash("password2"),
        )
        self.user_db.create(user)

        new_password = "new_password"
        self.user_db.update(user.get_data()[0], password=new_password)

        updated_user = self.user_db.read(user.get_data()[0])
        if updated_user is not None:
            self.assertTrue(
                argon2.PasswordHasher().verify(updated_user.get_data()[2], new_password)
            )

    def test_balance_update(self):
        user = User(
            "cccc-cccc-cccc-cccc",
            "test_user3",
            argon2.PasswordHasher().hash("password3"),
        )
        self.user_db.create(user)

        # Update the user's balance, expected should be delta because initial is zero
        delta_balance = 200.0
        expected_balance = delta_balance
        self.user_db.update(user.get_data()[0], delta_balance=delta_balance)

        updated_user = self.user_db.read(user.get_data()[0])
        if updated_user is not None:
            self.assertEqual(updated_user.get_data()[3], expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        self.user_db.delete("aaaa-aaaa-aaaa-aaaa")
        self.user_db.delete("bbbb-bbbb-bbbb-bbbb")
        self.user_db.delete("cccc-cccc-cccc-cccc")
        pass


class TestBankAuth(unittest.TestCase):
    def setUp(self):
        # Initialize a UserDatabase instance
        self.database = UserDatabase()
        self.bank = Bank(self.database)
        self.user = UserDT(
            "test_user",
            "password",
        )
        self.bank.register(self.user)

    def test_user_login_with_correct_password(self):
        self.assertTrue(self.bank.login(self.user))

    def test_user_login_with_incorrect_password(self):
        wrong_password_user = UserDT(
            "test_user",
            "wrong_password",
        )
        self.assertFalse(self.bank.login(wrong_password_user))

    def tearDown(self):
        # Clean up the database after tests
        user_data = self.database.read(username=self.user.username)
        if user_data is not None:
            uuid = user_data.get_data()[0]
            self.database.delete(uuid)


if __name__ == "__main__":
    unittest.main()
