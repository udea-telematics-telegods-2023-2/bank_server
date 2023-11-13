import unittest
import argon2
from bank_server import User, UserDatabase


class TestUserIntegration(unittest.TestCase):
    def setUp(self):
        # Initialize a UserDatabase instance
        self.user_db = UserDatabase()

    def test_user_creation_and_retrieval(self):
        # Create a user
        user1 = User(
            "aaaa-aaaa-aaaa-aaaa",
            "test_user1",
            argon2.PasswordHasher().hash("password1"),
        )

        # Add the user to the database
        self.user_db.create(user1)

        # Retrieve the user from the database
        retrieved_user = self.user_db.read(
            user1.get_data()[0]
        )  # Assuming the first element in the tuple is the UUID

        self.user_db.delete("aaaa-aaaa-aaaa-aaaa")

        self.assertIsNotNone(retrieved_user)

        # Assert that the retrieved user matches the original user
        if retrieved_user is not None:
            self.assertEqual(user1.get_data(), retrieved_user.get_data())

    def test_password_update(self):
        user2 = User(
            "bbbb-bbbb-bbbb-bbbb",
            "test_user2",
            argon2.PasswordHasher().hash("password2"),
        )
        self.user_db.create(user2)

        # Update the user's password
        new_password = "new_password"
        self.user_db.update(user2.get_data()[0], password=new_password)

        # Retrieve the updated user from the database
        updated_user = self.user_db.read(user2.get_data()[0])
        self.user_db.delete("bbbb-bbbb-bbbb-bbbb")
        if updated_user is not None:
            self.assertTrue(
                argon2.PasswordHasher().verify(updated_user.get_data()[2], new_password)
            )

    def test_balance_update(self):
        user3 = User(
            "cccc-cccc-cccc-cccc",
            "test_user3",
            argon2.PasswordHasher().hash("password3"),
        )
        self.user_db.create(user3)

        # Update the user's balance, because it starts with 0, expected should be delta
        delta_balance = 200.0
        expected_balance = delta_balance
        self.user_db.update(user3.get_data()[0], delta_balance=delta_balance)

        # Retrieve the updated user from the database
        updated_user = self.user_db.read(user3.get_data()[0])
        self.user_db.delete("cccc-cccc-cccc-cccc")

        if updated_user is not None:
            self.assertEqual(updated_user.get_data()[3], expected_balance)

    def tearDown(self):
        # Clean up the database after tests
        pass


if __name__ == "__main__":
    unittest.main()
