from typedmongo.expressions import RawExpression
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
    EnumField,
    FloatField,
    IntegerField,
    ListField,
    LiteralField,
    ObjectIdField,
    StringField,
    UnionField,
)
from .table import Document, Index, MongoDocument

# Alias for Document, for compatibility with older versions
Table = Document
MongoTable = MongoDocument

__all__ = [
    "RawExpression",
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
    "EnumField",
    "FloatField",
    "IntegerField",
    "ListField",
    "LiteralField",
    "ObjectIdField",
    "StringField",
    "UnionField",
]
