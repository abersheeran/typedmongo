import pytest
from bson import ObjectId
from marshmallow import ValidationError

import typedmongo.asyncio as mongo


class MongoTable(mongo.Table):
    _id: mongo.ObjectIdField


MongoTable.__lazy_init_fields__()


def test_objectid():
    assert MongoTable.load({"_id": "0123456789ab0123456789ab"})._id == ObjectId(
        "0123456789ab0123456789ab"
    )
    assert MongoTable.load({"_id": b"foo-bar-quux"})._id == ObjectId(
        "666f6f2d6261722d71757578"
    )


def test_invalid_objectid():
    with pytest.raises(ValidationError):
        MongoTable.load({"_id": "123"})
