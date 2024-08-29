import pytest
from bson import ObjectId
from marshmallow import ValidationError

import typedmongo.asyncio as mongo


class MongoDocument(mongo.Document):
    _id: mongo.ObjectIdField


MongoDocument.__lazy_init_fields__()


def test_objectid():
    assert MongoDocument.load({"_id": "0123456789ab0123456789ab"})._id == ObjectId(
        "0123456789ab0123456789ab"
    )
    assert MongoDocument.load({"_id": b"foo-bar-quux"})._id == ObjectId(
        "666f6f2d6261722d71757578"
    )


def test_invalid_objectid():
    with pytest.raises(ValidationError):
        MongoDocument.load({"_id": "123"})
