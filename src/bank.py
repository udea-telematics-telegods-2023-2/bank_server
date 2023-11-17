from src.db import User, UserDatabase
from dataclasses import dataclass


@dataclass
class PreUser:
    username: str
    password: str


class Bank:
    def __init__(self, database: UserDatabase):
        self.__database = database

    def register(self, pre_user: PreUser) -> bool:
        
        if pre_user.username 

        self.__database.create(user)
