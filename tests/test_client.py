from __future__ import annotations

from decimal import Decimal

import pytest
from pymongo import MongoClient

import typedmongo as mongo
from typedmongo.marshamallow import MarshamallowObjectId


class MongoTable(mongo.Table):
    __abstract__ = True

    _id: mongo.ObjectIdField = mongo.ObjectIdField(
        marshamallow=MarshamallowObjectId(required=False)
    )


class Wallet(mongo.Table):
    balance: mongo.DecimalField


class User(MongoTable):
    name: mongo.StringField
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    children: mongo.ListField[User]


# If use scope="module", the test will fail. Because pytest-asyncio close the event loop.
@pytest.fixture(scope="function", autouse=True)
def init_models():
    mongo.initial_collections(
        MongoClient().mongo,
        User,
    )
    yield
    User.objects.drop()


def test_use_objects_in_instance():
    with pytest.raises(AttributeError):
        User.load({}, partial=True).objects


@pytest.fixture
def document_id():
    document_id = User.objects.insert_one(
        User.load(
            {
                "name": "Aber",
                "age": 18,
                "tags": ["a", "b"],
                "wallet": {"balance": 100},
                "children": [],
            },
        )
    )
    yield document_id
    User.objects.delete_one(User._id == document_id)


def test_one_command(document_id):
    user = User.objects.find_one(User._id == document_id, sort=[+User.age])
    assert user is not None
    assert user.name == "Aber"
    assert user.wallet.balance == Decimal("100")

    update_result = User.objects.update_one(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e", "r"]}}
    )
    assert update_result.modified_count == 1

    user = User.objects.find_one(User._id == document_id)
    assert user is not None
    assert user.tags == ["a", "b", "e", "r"]

    delete_result = User.objects.delete_one(User._id == document_id)
    assert delete_result.deleted_count == 1


def test_find_one_and_command(document_id):
    user = User.objects.find_one_and_update(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e"]}}
    )
    assert user is not None
    assert user.tags == ["a", "b"]

    user = User.objects.find_one_and_update(
        User._id == document_id,
        {"$set": {"tags": ["a", "b", "e", "r"]}},
        after_document=True,
    )
    assert user is not None
    assert user.tags == ["a", "b", "e", "r"]

    user = User.objects.find_one_and_replace(
        User._id == document_id,
        User.load({"name": "Aber", "age": 0}),
        after_document=True,
    )
    assert user is not None
    assert user.age == 0

    user = User.objects.find_one_and_delete(User._id == document_id)
    assert user is not None
    assert user.name == "Aber"

    user = User.objects.find_one(User._id == document_id)
    assert user is None


@pytest.fixture
def documents_id():
    documents_id = User.objects.insert_many(
        User.load(
            {
                "name": "Aber",
                "age": 18,
                "tags": ["a", "b"],
                "wallet": {"balance": 100},
                "children": [],
            },
        ),
        User.load(
            {
                "name": "Yue",
                "age": 18,
                "tags": ["y", "u"],
                "wallet": {"balance": 200},
                "children": [],
            },
        ),
    )
    yield documents_id
    User.objects.delete_many({"_id": {"$in": documents_id}})


def test_many_comand(documents_id):
    users = [user for user in User.objects.find(User.age == 18, sort=[-User.age])]
    assert len(users) == 2

    users = [user for user in User.objects.find({"_id": {"$in": documents_id}})]
    assert len(users) == len(documents_id)

    update_result = User.objects.update_many(
        User.wallet._.balance == Decimal("100"), {"$inc": {"wallet.balance": 10}}
    )
    assert update_result.modified_count == 1
    user = User.objects.find_one(User.wallet._.balance == Decimal("110"))
    assert user is not None
    assert user.wallet.balance == Decimal(110)

    assert User.objects.count_documents(User.age >= 0) == 2


def test_bulk_write(documents_id):
    User.objects.bulk_write(
        mongo.DeleteOne(User._id == 0),
        mongo.DeleteMany(User.age < 18),
        mongo.InsertOne(User.load({"name": "InsertOne"}, partial=True)),
        mongo.ReplaceOne(User.name == "Aber", User.load({}, partial=True)),
        mongo.UpdateMany({}, {"$set": {"age": 25}}),
        mongo.UpdateMany(User.name == "Yue", {"$set": {"name": "yue"}}),
    )


User.__lazy_init_fields__()


@pytest.mark.parametrize(
    "expression",
    [
        User.name == "Aber",
        User.name != "Aber",
        (User.name == "Aber") & (User.age == 18),
        (User.name == "Aber") | (User.age > 20),
        (User.name == "Aber") & (User.age <= 20),
        (User.name == "Aber") & ~(User.age > 20),
    ],
)
def test_filter_expressions(documents_id, expression):
    assert User.objects.count_documents(expression) == 1
