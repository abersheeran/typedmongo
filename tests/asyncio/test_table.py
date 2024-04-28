from __future__ import annotations

import uuid

import pytest

import typedmongo.asyncio as mongo
from typedmongo.expressions import Expression


class MongoTable(mongo.Table):
    __abstract__ = True

    _id: mongo.StringField = mongo.StringField(default=lambda: uuid.uuid4().hex)


class Wallet(mongo.Table):
    balance: mongo.DecimalField


class User(MongoTable):
    name: mongo.StringField
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    children: mongo.ListField[User]
    extra: mongo.DictField = mongo.DictField(default=dict)


User.__lazy_init_fields__()


@pytest.mark.parametrize(
    "expression, repr_str",
    [
        (
            User.name == "Aber",
            "CompareExpression(field=name, operator='==', arg='Aber')",
        ),
        (
            User.age >= 18,
            "CompareExpression(field=age, operator='>=', arg=18)",
        ),
        (
            User.tags == "a",
            "CompareExpression(field=tags, operator='==', arg='a')",
        ),
        (
            User.tags[0] == "0",
            "CompareExpression(field=tags.0, operator='==', arg='0')",
        ),
        (
            User.wallet._.balance > 1,
            "CompareExpression(field=wallet.balance, operator='>', arg=1)",
        ),
        (
            User.children[0].name == "Yue",
            "CompareExpression(field=children.0.name, operator='==', arg='Yue')",
        ),
        (
            User.children._.age >= 18,
            "CompareExpression(field=children.age, operator='>=', arg=18)",
        ),
        (
            User.extra == {"a": "b"},
            "CompareExpression(field=extra, operator='==', arg={'a': 'b'})",
        ),
    ],
)
def test_expression(expression, repr_str):
    assert isinstance(expression, Expression)
    assert repr(expression) == repr_str


def test_field_default():
    user = User.load(
        {
            "name": "Aber",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
        }
    )
    assert isinstance(user._id, str)

    user = User.load(
        {
            "name": "Aber",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
        },
        partial=True,
    )
    assert isinstance(user._id, str)

    user = User(
        name="Aber", age=18, tags=["a", "b"], wallet=Wallet(balance=100), children=[]
    )
    assert not hasattr(user, "_id")
    assert isinstance(user.dump(user)["_id"], str)


def test_recursion_field():
    user = User.load(
        {
            "name": "Aber",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [
                {
                    "name": "Yue",
                    "age": 18,
                    "tags": ["a", "b"],
                    "wallet": {"balance": 100},
                    "children": [],
                }
            ],
        }
    )
    assert isinstance(user.wallet, Wallet)
    assert user.wallet.balance == 100
    assert isinstance(user.children[0], User)
    assert user.children[0].name == "Yue"
    assert isinstance(user.children[0]._id, str)


def test_empty_field():
    user = User.load({}, partial=True)
    assert not hasattr(user, "name")
    assert hasattr(user, "_id")


def test_dict_field():
    user = User.load(
        {
            "name": "Aber",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
            "extra": {"a": "b"},
        }
    )
    assert user.extra == {"a": "b"}
    assert user.dump(user)["extra"] == {"a": "b"}
