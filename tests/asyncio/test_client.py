from __future__ import annotations

from decimal import Decimal

import pytest
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import typedmongo.asyncio as mongo


class Wallet(mongo.Document):
    balance: mongo.DecimalField


class User(mongo.MongoDocument):
    name: mongo.StringField
    age: mongo.IntegerField
    tags: mongo.DynamicField[list[str]]
    wallet: mongo.EmbeddedField[Wallet]
    children: mongo.DynamicField[list[User]]

    @classmethod
    def indexes(cls) -> list[mongo.Index]:
        super_indexes = super().indexes()
        return [*super_indexes, mongo.Index(cls.age)]


# If use scope="module", the test will fail. Because pytest-asyncio close the event loop.
@pytest.fixture(scope="function", autouse=True)
async def init_models():
    await mongo.initial_collections(
        MongoClient().mongo,
        User,
    )
    yield
    await User.objects.collection.drop()


async def test_use_objects_in_instance():
    with pytest.raises(AttributeError):
        User.load({}, partial=True).objects


@pytest.fixture
async def document_id():
    document_id = await User.objects.insert_one(
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
    await User.objects.delete_one(User._id == document_id)


async def test_one_command(document_id):
    user = await User.objects.find_one(User._id == document_id, sort=[+User.age])
    assert user is not None
    assert user.name == "Aber"
    assert user.wallet.balance == Decimal("100")

    update_result = await User.objects.update_one(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e", "r"]}}
    )
    assert update_result.modified_count == 1

    user = await User.objects.find_one(User._id == document_id)
    assert user is not None
    assert user.tags == ["a", "b", "e", "r"]

    delete_result = await User.objects.delete_one(User._id == document_id)
    assert delete_result.deleted_count == 1


async def test_find_one_and_command(document_id):
    user = await User.objects.find_one_and_update(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e"]}}
    )
    assert user is not None
    assert user.tags == ["a", "b"]

    user = await User.objects.find_one_and_update(
        User._id == document_id,
        {"$set": {"tags": ["a", "b", "e", "r"]}},
        after_document=True,
    )
    assert user is not None
    assert user.tags == ["a", "b", "e", "r"]

    user = await User.objects.find_one_and_replace(
        User._id == document_id,
        User.load({"name": "Aber", "age": 0}),
        after_document=True,
    )
    assert user is not None
    assert user.age == 0

    user = await User.objects.find_one_and_delete(User._id == document_id)
    assert user is not None
    assert user.name == "Aber"

    user = await User.objects.find_one(User._id == document_id)
    assert user is None


@pytest.fixture
async def documents_id():
    documents_id = await User.objects.insert_many(
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
    await User.objects.delete_many({"_id": {"$in": documents_id}})


async def test_many_comand(documents_id):
    users = [user async for user in User.objects.find(User.age == 18, sort=[-User.age])]
    assert len(users) == 2

    users = [user async for user in User.objects.find({"_id": {"$in": documents_id}})]
    assert len(users) == len(documents_id)

    update_result = await User.objects.update_many(
        User.wallet._.balance == Decimal("100"), {"$inc": {"wallet.balance": 10}}
    )
    assert update_result.modified_count == 1
    user = await User.objects.find_one(User.wallet._.balance == Decimal("110"))
    assert user is not None
    assert user.wallet.balance == Decimal(110)

    assert await User.objects.count_documents(User.age >= 0) == 2


async def test_bulk_write(documents_id):
    await User.objects.bulk_write(
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
async def test_filter_expressions(documents_id, expression):
    assert await User.objects.count_documents(expression) == 1


@pytest.mark.parametrize(
    "projection",
    [
        [User.name],
        {User.name: True, User._id: False},
    ],
)
async def test_projection(documents_id, projection):
    user = await User.objects.find_one(User.age == 18, projection=projection)
    assert user is not None


@pytest.mark.parametrize(
    "shortcut",
    [
        mongo.Contains("be"),
        mongo.Contains("bE", case_sensitive=False),
        mongo.StartsWith("A"),
        mongo.StartsWith("a", case_sensitive=False),
        mongo.EndsWith("r"),
        mongo.EndsWith("R", case_sensitive=False),
    ],
)
async def test_shortcut(documents_id, shortcut):
    user = await User.objects.find_one(User.name == shortcut)
    assert user is not None
    assert user.name == "Aber"


async def test_transaction(documents_id):
    async with User.objects.use_session():
        await User.objects.update_many({}, {"$set": {"age": 20}})
        await User.objects.delete_many(User.name == "Aber")
        await User.objects.insert_one(User.load({"name": "Aber", "age": 18}))
