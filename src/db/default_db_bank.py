#!/usr/bin/python

import uuid

from argon2 import PasswordHasher
from src.db import db

# Static user data
usernames = ["donCESAR12345", "evil_leal", "johan", "yuruk", "sanket"]
passwords = ["soyunserdeluz", "tele", "cesarteodio", "genshin123", "funcional"]

# UUID for each user, username, hashed password and initial balance
ph = PasswordHasher()
clients = [db.User(str(uuid.uuid4()), username, ph.hash(password))
    for username, password in zip(usernames, passwords)
]

# Create new database
database = db.UserDatabase()

# Insert default clients
for client in clients:
    database.create(client)
