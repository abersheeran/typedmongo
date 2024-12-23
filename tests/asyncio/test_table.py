from __future__ import annotations

import datetime
import uuid
from typing import Literal

import pytest

import typedmongo.asyncio as mongo
from typedmongo.expressions import Expression


class MongoDocument(mongo.Document):
    __abstract__ = True

    _id: mongo.StringField = mongo.StringField(default=lambda: uuid.uuid4().hex)


class Wallet(mongo.Document):
    balance: mongo.DecimalField


class Social(mongo.Document):
    site: mongo.StringField
    user: mongo.StringField


class User(MongoDocument):
    name: mongo.StringField
    gender: mongo.LiteralField[Literal["m", "f"]]
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    created_at: mongo.DateTimeField = mongo.DateTimeField(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    children: mongo.ListField[User]
    socials: mongo.ListField[Social] = mongo.ListField(
        mongo.EmbeddedField(Social), default=list
    )
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


def test_list_field():
    user = User.load(
        {
            "name": "Aber",
            "gender": "m",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
            "socials": [{"site": "github.com", "user": "abersheeran"}],
        }
    )
    assert user.socials == [Social(site="github.com", user="abersheeran")]


def test_field_default():
    user = User.load(
        {
            "name": "Aber",
            "gender": "m",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
        }
    )
    assert isinstance(user._id, str)
    assert isinstance(user.created_at, datetime.datetime)

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
    assert isinstance(user.created_at, datetime.datetime)

    user = User(
        name="Aber",
        gender="m",
        age=18,
        tags=["a", "b"],
        wallet=Wallet(balance=100),
        children=[],
    )
    assert hasattr(user, "_id")
    assert isinstance(User.dump(user)["_id"], str)
    assert isinstance(user.created_at, datetime.datetime)


def test_recursion_field():
    user = User.load(
        {
            "name": "Aber",
            "gender": "m",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [
                {
                    "name": "Yue",
                    "gender": "f",
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
            "gender": "m",
            "age": 18,
            "tags": ["a", "b"],
            "wallet": {"balance": 100},
            "children": [],
            "extra": {"a": "b"},
        }
    )
    assert user.extra == {"a": "b"}
    assert user.dump()["extra"] == {"a": "b"}


def test_datetime_field():
    user = User.load(dict(created_at=datetime.datetime.now()), partial=True)
    assert isinstance(user.created_at, datetime.datetime)


def test_literal_field():
    user = User.load(dict(gender="m"), partial=True)
    assert user.gender == "m"


def test_embedded_field():
    user = User.load({"wallet": {"balance": 100}}, partial=True)
    assert isinstance(user.wallet, Wallet)
    assert user.wallet.balance == 100


class UserWithRole(User):
    role: mongo.LiteralField[Literal["admin", "user"]]


UserWithRole.__lazy_init_fields__()


def test_three_level_inheritance():
    user = UserWithRole.load(dict(role="admin"), partial=True)
    assert isinstance(user._id, str)


class U(mongo.Document):
    normal_type: mongo.UnionField[int | str]
    list_type: mongo.ListField[int | str]
    embedded_type: mongo.UnionField[UserWithRole | User]


U.__lazy_init_fields__()


def test_union_field():
    u = U.load({"normal_type": 1}, partial=True)
    assert u.normal_type == 1
    u = U.load({"normal_type": "1"}, partial=True)
    assert u.normal_type == "1"

    u = U.load({"list_type": [1, "1"]}, partial=True)
    assert u.list_type == [1, "1"]

    u = U.load({"embedded_type": {"role": "admin"}}, partial=True)
    assert isinstance(u.embedded_type, UserWithRole)
    assert u.embedded_type.role == "admin"

    u = U.load({"embedded_type": {"name": "Aber"}}, partial=True)
    assert isinstance(u.embedded_type, User)
    assert u.embedded_type.name == "Aber"
