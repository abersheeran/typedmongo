from __future__ import annotations

import enum
from decimal import Decimal

import pytest
from pymongo.synchronous.mongo_client import MongoClient

import typedmongo as mongo


class Wallet(mongo.Document):
    balance: mongo.DecimalField


class Gender(enum.Enum):
    MALE = "m"
    FEMALE = "f"


class User(mongo.MongoDocument):
    name: mongo.StringField
    gender: mongo.EnumField[Gender]
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    children: mongo.ListField[User]

    @classmethod
    def indexes(cls) -> list[mongo.Index]:
        super_indexes = super().indexes()
        return [*super_indexes, mongo.Index(cls.age)]


# If use scope="module", the test will fail. Because pytest-asyncio close the event loop.
@pytest.fixture(scope="function", autouse=True)
def init_models():
    mongo.initial_collections(
        MongoClient().mongo,
        User,
    )
    yield
    User.objects.collection.drop()


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
                "gender": "m",
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
        User.load({"name": "Aber", "age": 0}, partial=True),
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
                "gender": "m",
                "tags": ["a", "b"],
                "wallet": {"balance": 100},
                "children": [],
            },
        ),
        User.load(
            {
                "name": "Yue",
                "age": 18,
                "gender": "f",
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


@pytest.mark.parametrize(
    "projection",
    [
        [User.name],
        {User.name: True, User._id: False},
    ],
)
def test_projection(documents_id, projection):
    user = User.objects.find_one(User.age == 18, projection=projection)
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
def test_shortcut(documents_id, shortcut):
    user = User.objects.find_one(User.name == shortcut)
    assert user is not None
    assert user.name == "Aber"


def test_transaction(documents_id):
    with User.objects.use_session():
        User.objects.update_many({}, {"$set": {"age": 20}})
        User.objects.delete_many(User.name == "Aber")
        User.objects.insert_one(
            User.load({"name": "Aber", "age": 18}, partial=True)
        )


def test_collection_not_initialized():
    """Test Manager.collection raises AttributeError when not initialized - covers lines 140-141"""
    # Create a new document class without initializing collections
    class UninitializedDoc(mongo.MongoDocument):
        name: mongo.StringField

    # Try to access collection before initialization
    with pytest.raises(AttributeError, match="has not been initialized"):
        _ = UninitializedDoc.objects.collection


def test_use_transaction_with_options():
    """Test Manager.use_transaction with session options - covers lines 185-192"""
    from pymongo.read_concern import ReadConcern
    from pymongo.read_preferences import ReadPreference
    from pymongo.write_concern import WriteConcern

    # Test use_transaction with custom options
    with User.objects.use_transaction(
        read_concern=ReadConcern("majority"),
        write_concern=WriteConcern(w=1),
        read_preference=ReadPreference.PRIMARY,
        max_commit_time_ms=5000,
    ):
        # Insert a document in transaction
        User.objects.insert_one(
            User.load(
                {
                    "name": "Transaction Test",
                    "age": 25,
                    "gender": "m",
                    "tags": ["test"],
                    "wallet": {"balance": 100},
                    "children": [],
                },
            )
        )

    # Verify the document was inserted
    user = User.objects.find_one(User.name == "Transaction Test")
    assert user is not None
    User.objects.delete_one(User._id == user._id)


def test_find_one_and_update_not_found():
    """Test find_one_and_update returning None - covers line 267"""
    # Try to update a non-existent document
    result = User.objects.find_one_and_update(
        User.name == "NonExistentUser12345", {"$set": {"age": 99}}
    )
    assert result is None


def test_find_one_and_replace_not_found():
    """Test find_one_and_replace returning None - covers line 311"""
    # Try to replace a non-existent document
    result = User.objects.find_one_and_replace(
        User.name == "NonExistentUser12345",
        User.load({"name": "Replacement", "age": 99}, partial=True),
    )
    assert result is None


def test_find_one_and_delete_not_found():
    """Test find_one_and_delete returning None - covers line 359"""
    # Try to delete a non-existent document
    result = User.objects.find_one_and_delete(User.name == "NonExistentUser12345")
    assert result is None


def test_update_one_to_mongo():
    """Test UpdateOne.to_mongo method - covers line 498"""
    # Create an UpdateOne instance
    update_op = mongo.UpdateOne(User.name == "Test", {"$set": {"age": 30}}, upsert=True)

    # Call to_mongo to get the MongoDB operation
    mongo_op = update_op.to_mongo()

    # Verify the operation structure
    assert mongo_op is not None
    assert hasattr(mongo_op, "_filter")
    assert hasattr(mongo_op, "_doc")
