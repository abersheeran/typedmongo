from typedmongo.shortcuts import Contains, EndsWith, StartsWith

from .client import (
    DeleteMany,
    DeleteOne,
    InsertOne,
    ReplaceOne,
    UpdateMany,
    UpdateOne,
    initial_collections,
)
from .fields import (
    BooleanField,
    DateTimeField,
    DecimalField,
    DictField,
    EmbeddedField,
    FieldParamters,
    FloatField,
    IntegerField,
    LiteralField,
    ObjectIdField,
    StringField,
)
from .table import Document, Index, MongoDocument

# Alias for Document, for compatibility with older versions
Table = Document
MongoTable = MongoDocument

__all__ = [
    "Contains",
    "StartsWith",
    "EndsWith",
    "DeleteMany",
    "DeleteOne",
    "InsertOne",
    "ReplaceOne",
    "UpdateMany",
    "UpdateOne",
    "initial_collections",
    "Index",
    "MongoDocument",
    "Document",
    "BooleanField",
    "DateTimeField",
    "DecimalField",
    "DictField",
    "EmbeddedField",
    "FieldParamters",
    "FloatField",
    "IntegerField",
    "LiteralField",
    "ObjectIdField",
    "StringField",
]
