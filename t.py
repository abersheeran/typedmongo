from __future__ import annotations

from typedmongo.table import Table
from typedmongo import fields


class Wallet(Table):
    balance = fields.FloatField()


class User(Table):
    name: fields.StringField
    age: fields.IntegerField
    tags: fields.ListField[str]
    wallet: fields.EmbeddedField[Wallet]
    children: fields.ListField[User]


User.__lazy_init_fields__()

print(User.name == "Aber")
print(User.age >= 18)
print(User.tags == "a")
print(User.tags[0] == "0")
print(User.wallet._.balance > 1)
print(User.children[0].name == "Aber")
print(User.children._.age >= 18)

user = User.load(
    {
        "name": "John",
        "age": 20,
        "tags": ["a", "b"],
        "wallet": {"balance": 100.0},
        "children": [],
        "unknown": "value",
    },
    partial=True,
)
user.name
user.age
user.wallet
user.children
print(user)
