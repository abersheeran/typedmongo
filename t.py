from __future__ import annotations

import pymongo

import typedmongo


class Wallet(typedmongo.Table):
    balance = typedmongo.FloatField()


class User(typedmongo.Table):
    name: typedmongo.StringField
    age: typedmongo.IntegerField
    tags: typedmongo.ListField[str]
    wallet: typedmongo.EmbeddedField[Wallet]
    children: typedmongo.ListField[User]


typedmongo.initial_collections(
    pymongo.MongoClient().typedmongo,
    User,
    Wallet,
)

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

for user in User.objects.find(
    (User.name == "Aber") & (User.age >= 18), [User.name, User.age]
):
    print(user)
