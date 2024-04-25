from __future__ import annotations

import pytest
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import typedmongo.asyncio as mongo


class MongoTable(mongo.Table):
    __abstract__ = True

    _id: mongo.ObjectIdField


class Wallet(mongo.Table):
    balance: mongo.DecimalField


class User(MongoTable):
    name: mongo.StringField
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    children: mongo.ListField[User]


@pytest.fixture(scope="module", autouse=True)
async def init_models():
    await mongo.initial_collections(
        MongoClient().mongo,
        User,
    )


async def test_insert_one():
    document_id = await User.objects.insert_one(
        User.load(
            {
                "name": "Aber",
                "age": 18,
                "tags": ["a", "b"],
                "wallet": {"balance": 100},
                "children": [],
            },
            partial=True,
        )
    )
    user = await User.objects.find_one(User._id == document_id)
    assert user is not None
    assert user.name == "Aber"
