from __future__ import annotations

import dataclasses
import decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Generic,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    TypeAlias,
    TypeVar,
    overload,
)

from bson.codec_options import CodecOptions, TypeCodec, TypeRegistry
from bson.decimal128 import Decimal128
from pymongo.operations import DeleteMany as MongoDeleteMany
from pymongo.operations import DeleteOne as MongoDeleteOne
from pymongo.operations import InsertOne as MongoInsertOne
from pymongo.operations import ReplaceOne as MongoReplaceOne
from pymongo.operations import UpdateMany as MongoUpdateMany
from pymongo.operations import UpdateOne as MongoUpdateOne

if TYPE_CHECKING:
    from pymongo.collection import Collection as MongoCollection
    from pymongo.database import Database as MongoDatabase
    from pymongo.results import BulkWriteResult as MongoBlukWriteResult
    from pymongo.results import DeleteResult as MongoDeleteResult
    from pymongo.results import UpdateResult as MongoUpdateResult

    from .table import Table

from typedmongo.expressions import Expression, OrderBy, compile_expression

from .fields import Field

T = TypeVar("T", bound="Table")


class DecimalCodec(TypeCodec):
    python_type = decimal.Decimal  # type: ignore
    bson_type = Decimal128  # type: ignore

    def transform_python(self, value: decimal.Decimal) -> Decimal128:
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        return Decimal128(value)

    def transform_bson(self, value: Decimal128) -> decimal.Decimal:
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        return value.to_decimal()


def initial_collections(db: MongoDatabase, *tables: type[Table]) -> None:
    for table in tables:
        table.__lazy_init_fields__()
        table.__database__ = db
        type_registry = TypeRegistry([DecimalCodec()])
        codec_options = CodecOptions(type_registry=type_registry)
        table.__collection__ = collection = db.get_collection(
            table.__collection_name__, codec_options=codec_options
        )
        indexes = table.indexes()
        if indexes:
            collection.create_indexes(
                [index.to_index_model() for index in indexes]
            )


class Manager:
    @overload
    def __get__(self, instance: None, cls: type[T]) -> Objects[T]: ...

    @overload
    def __get__(self, instance: T, cls: type[T]) -> NoReturn: ...

    def __get__(self, instance, cls):
        if instance is None:
            return Objects(cls)

        raise AttributeError("Manager is not accessible via instance")


DocumentId: TypeAlias = Any
Filter = Expression | dict[Any, Any]
Projection: TypeAlias = list[Field] | dict[Field, bool] | dict[str, bool]
Sort: TypeAlias = list[OrderBy] | list[tuple[str, Literal[1, -1]]]

translate_filter = (
    lambda f: {}
    if f is None
    else (compile_expression(f) if isinstance(f, Expression) else f)
)
translate_projection = (
    lambda p: None
    if p is None
    else (
        [f.field_name for f in p]
        if isinstance(p, list)
        else {f.field_name if isinstance(f, Field) else f: v for f, v in p.items()}
    )
)
translate_sort = (
    lambda s: None
    if s is None
    else [
        (order_by.field.field_name, order_by.order)
        if isinstance(order_by, OrderBy)
        else order_by
        for order_by in s
    ]
)


class Objects(Generic[T]):
    def __init__(self, table: type[T]) -> None:
        self.table = table

    @property
    def collection(self) -> MongoCollection:
        return self.table.__collection__

    def insert_one(self, document: T) -> DocumentId:
        insert_result = self.collection.insert_one(document.to_mongo())
        return insert_result.inserted_id

    def insert_many(
        self, *documents: T, ordered: bool = True
    ) -> list[DocumentId]:
        insert_result = self.collection.insert_many(
            [document.to_mongo() for document in documents], ordered=ordered
        )
        return insert_result.inserted_ids

    def find(
        self,
        filter: Optional[Filter] = None,
        projection: Optional[Projection] = None,
        skip: int = 0,
        limit: int = 0,
        sort: Optional[Sort] = None,
        allow_disk_use: Optional[bool] = None,
    ) -> Iterable[T]:
        for document in self.collection.find(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            skip=skip,
            limit=limit,
            sort=translate_sort(sort),
            allow_disk_use=allow_disk_use,
        ):
            yield self.table.load(document, partial=True)

    def find_one(
        self,
        filter: Optional[Filter] = None,
        projection: Optional[Projection] = None,
        skip: int = 0,
        sort: Optional[Sort] = None,
        allow_disk_use: Optional[bool] = None,
    ) -> T | None:
        document = self.collection.find_one(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            skip=skip,
            sort=translate_sort(sort),
            allow_disk_use=allow_disk_use,
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    def find_one_and_delete(
        self,
        filter: Filter,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
    ) -> T | None:
        document = self.collection.find_one_and_delete(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            sort=translate_sort(sort),
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    def find_one_and_replace(
        self,
        filter: Filter,
        replacement: T,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: bool = False,
        after_document: bool = False,
    ) -> T | None:
        document = self.collection.find_one_and_replace(
            filter=translate_filter(filter),
            replacement=replacement.to_mongo(),
            projection=translate_projection(projection),
            sort=translate_sort(sort),
            upsert=upsert,
            return_document=after_document,
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    def find_one_and_update(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: bool = False,
        after_document: bool = False,
    ) -> T | None:
        document = self.collection.find_one_and_update(
            filter=translate_filter(filter),
            update=update,
            projection=translate_projection(projection),
            sort=translate_sort(sort),
            upsert=upsert,
            return_document=after_document,
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    def delete_one(
        self,
        filter: Optional[Filter] = None,
    ) -> MongoDeleteResult:
        return self.collection.delete_one(translate_filter(filter))

    def delete_many(
        self,
        filter: Optional[Filter] = None,
    ) -> MongoDeleteResult:
        return self.collection.delete_many(translate_filter(filter))

    def update_one(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        upsert: bool = False,
    ) -> MongoUpdateResult:
        return self.collection.update_one(
            translate_filter(filter),
            update,
            upsert=upsert,
        )

    def update_many(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        upsert: bool = False,
    ) -> MongoUpdateResult:
        return self.collection.update_many(
            translate_filter(filter),
            update,
            upsert=upsert,
        )

    def count_documents(
        self,
        filter: Filter,
    ) -> int:
        return self.collection.count_documents(translate_filter(filter))

    def bulk_write(
        self,
        *requests: DeleteMany
        | DeleteOne
        | InsertOne[T]
        | ReplaceOne[T]
        | UpdateMany
        | UpdateOne,
        ordered: bool = True,
    ) -> MongoBlukWriteResult:
        return self.collection.bulk_write(
            [r.to_mongo() for r in requests], ordered=ordered
        )


@dataclasses.dataclass
class DeleteMany:
    filter: Filter

    def to_mongo(self) -> MongoDeleteMany:
        return MongoDeleteMany(translate_filter(self.filter))


@dataclasses.dataclass
class DeleteOne:
    filter: Filter

    def to_mongo(self) -> MongoDeleteOne:
        return MongoDeleteOne(translate_filter(self.filter))


@dataclasses.dataclass
class InsertOne(Generic[T]):
    document: T

    def to_mongo(self) -> MongoInsertOne:
        return MongoInsertOne(self.document.to_mongo())


@dataclasses.dataclass
class ReplaceOne(Generic[T]):
    filter: Filter
    replacement: T

    def to_mongo(self) -> MongoReplaceOne:
        return MongoReplaceOne(
            translate_filter(self.filter), self.replacement.to_mongo()
        )


@dataclasses.dataclass
class UpdateMany:
    filter: Filter
    update: Mapping[str, Any] | list[Mapping[str, Any]]
    upsert: bool = False

    def to_mongo(self) -> MongoUpdateMany:
        return MongoUpdateMany(
            translate_filter(self.filter), self.update, upsert=self.upsert
        )


@dataclasses.dataclass
class UpdateOne:
    filter: Filter
    update: Mapping[str, Any] | list[Mapping[str, Any]]
    upsert: bool = False

    def to_mongo(self) -> MongoUpdateOne:
        return MongoUpdateOne(
            translate_filter(self.filter), self.update, upsert=self.upsert
        )
