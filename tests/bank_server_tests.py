import unittest
import argon2
from src.db import User, UserDatabase, make_hash


class TestBankDB(unittest.TestCase):
    def setUp(self):
        # Initialize a UserDatabase instance
        self.user_db = UserDatabase()

    def test_user_creation_and_retrieval_by_uuid(self):
        # Create a user
        user = User(
            "aaaa-aaaa-aaaa-aaaa",
            "test_user1",
            make_hash("password1"),
        )

        # Add the user to the database
        self.user_db.create(user)

        # Retrieve the user from the database
        retrieved_user = self.user_db.read(uuid=user.get_data()[0])

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(user.get_data(), retrieved_user.get_data())

    def test_user_creation_and_retrieval_by_username(self):
        # Create a user
        user = User(
            "bbbb-bbbb-bbbb-bbbb",
            "test_user2",
            make_hash("password2"),
        )

        # Add the user to the database
        self.user_db.create(user)

        # Retrieve the user from the database
        retrieved_user = self.user_db.read(username=user.get_data()[1])

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(user.get_data(), retrieved_user.get_data())

    def test_user_retrieval_without_parameters(self):
        # Retrieve the user from the database
        retrieved_user = self.user_db.read()

        self.assertIsNone(retrieved_user)

    def test_password_update(self):
        user = User(
            "cccc-cccc-cccc-cccc",
            "test_user3",
            argon2.PasswordHasher().hash("password3"),
        )
        self.user_db.create(user)

        # Update the user's password
        new_password = "new_password"
        self.user_db.update(user.get_data()[0], password=new_password)

        # Retrieve the updated user from the database
        updated_user = self.user_db.read(user.get_data()[0])
        if updated_user is not None:
            self.assertTrue(
                argon2.PasswordHasher().verify(updated_user.get_data()[2], new_password)
            )

    def test_balance_update(self):
        user = User(
            "dddd-dddd-dddd-dddd",
            "test_user4",
            argon2.PasswordHasher().hash("password4"),
        )
        self.user_db.create(user)

        # Update the user's balance, because it starts with 0, expected should be delta
        delta_balance = 200.0
        expected_balance = delta_balance
        self.user_db.update(user.get_data()[0], delta_balance=delta_balance)

        # Retrieve the updated user from the database
        updated_user = self.user_db.read(user.get_data()[0])

        if updated_user is not None:
            self.assertEqual(updated_user.get_data()[3], expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        self.user_db.delete("aaaa-aaaa-aaaa-aaaa")
        self.user_db.delete("bbbb-bbbb-bbbb-bbbb")
        self.user_db.delete("cccc-cccc-cccc-cccc")
        self.user_db.delete("dddd-dddd-dddd-dddd")
        pass


if __name__ == "__main__":
    unittest.main()
