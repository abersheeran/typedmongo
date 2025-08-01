from __future__ import annotations

import dataclasses
import decimal
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterable,
    Generic,
    List,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    Sequence,
    TypeAlias,
    TypeVar,
    overload,
)

from bson.codec_options import CodecOptions, TypeCodec, TypeRegistry
from bson.decimal128 import Decimal128
from pymongo.asynchronous.client_session import TransactionOptions
from pymongo.operations import DeleteMany as MongoDeleteMany
from pymongo.operations import DeleteOne as MongoDeleteOne
from pymongo.operations import InsertOne as MongoInsertOne
from pymongo.operations import ReplaceOne as MongoReplaceOne
from pymongo.operations import UpdateMany as MongoUpdateMany
from pymongo.operations import UpdateOne as MongoUpdateOne
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import ReadPreference, _ServerMode
from pymongo.write_concern import WriteConcern

if TYPE_CHECKING:
    from pymongo.asynchronous.client_session import AsyncClientSession as MongoSession
    from pymongo.asynchronous.collection import AsyncCollection as MongoCollection
    from pymongo.asynchronous.database import AsyncDatabase as MongoDatabase
    from pymongo.results import BulkWriteResult as MongoBlukWriteResult
    from pymongo.results import DeleteResult as MongoDeleteResult
    from pymongo.results import UpdateResult as MongoUpdateResult

    from .table import Document

from typedmongo.expressions import Expression, OrderBy, compile_expression

from .fields import Field

T = TypeVar("T", bound="Document")


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


async def initial_collections(db: MongoDatabase, *tables: type[Document]) -> None:
    for table in tables:
        table.__lazy_init_fields__()
        table.__database__ = db
        type_registry = TypeRegistry([DecimalCodec()])
        codec_options = CodecOptions(type_registry=type_registry, tz_aware=True)
        table.__collection__ = collection = db.get_collection(
            table.__collection_name__, codec_options=codec_options
        )
        indexes = table.indexes()
        if indexes:
            await collection.create_indexes(
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

SESSION: ContextVar[Optional[MongoSession]] = ContextVar("session", default=None)


class Objects(Generic[T]):
    def __init__(self, table: type[T]) -> None:
        self.table = table

    @property
    def collection(self) -> MongoCollection:
        try:
            return self.table.__collection__
        except AttributeError:
            raise AttributeError(
                f"Document '{self.table.__name__}' has not been initialized"
            )

    @asynccontextmanager
    async def use_session(
        self,
        causal_consistency: bool | None = None,
        default_transaction_options: TransactionOptions | None = None,
        snapshot: bool | None = False,
    ) -> AsyncGenerator[MongoSession, None]:
        """
        Use a session to execute operations, for example:

        ```python
        async with Document.objects.use_session() as session:
            await Document.objects.insert_one(document)
        """
        async with self.collection.database.client.start_session(
            causal_consistency=causal_consistency,
            default_transaction_options=default_transaction_options,
            snapshot=snapshot,
        ) as session:
            token = SESSION.set(session)
            try:
                yield session
            finally:
                SESSION.reset(token)

    @asynccontextmanager
    async def use_transaction(
        self,
        read_concern: Optional[ReadConcern] = None,
        write_concern: Optional[WriteConcern] = None,
        read_preference: _ServerMode = ReadPreference.PRIMARY,
        max_commit_time_ms: Optional[int] = None,
    ) -> AsyncGenerator[MongoSession, None]:
        """
        Use a transaction to execute operations, for example:

        ```python
        async with Document.objects.use_transaction():
            await Document.objects.insert_one(document)
        """
        async with self.use_session() as session:
            async with await session.start_transaction(
                read_concern=read_concern,
                write_concern=write_concern,
                read_preference=read_preference,
                max_commit_time_ms=max_commit_time_ms,
            ):
                yield session

    async def insert_one(self, document: T) -> DocumentId:
        insert_result = await self.collection.insert_one(
            document.to_mongo(), session=SESSION.get()
        )
        return insert_result.inserted_id

    async def insert_many(
        self, *documents: T, ordered: bool = True
    ) -> list[DocumentId]:
        insert_result = await self.collection.insert_many(
            [document.to_mongo() for document in documents],
            ordered=ordered,
            session=SESSION.get(),
        )
        return insert_result.inserted_ids

    async def find(
        self,
        filter: Optional[Filter] = None,
        projection: Optional[Projection] = None,
        skip: int = 0,
        limit: int = 0,
        sort: Optional[Sort] = None,
        allow_disk_use: Optional[bool] = None,
        no_cursor_timeout: bool = False,
        max_time_ms: Optional[int] = None,
    ) -> AsyncIterable[T]:
        async for document in self.collection.find(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            skip=skip,
            limit=limit,
            sort=translate_sort(sort),
            allow_disk_use=allow_disk_use,
            no_cursor_timeout=no_cursor_timeout,
            max_time_ms=max_time_ms,
            session=SESSION.get(),
        ):
            yield self.table.load(document, partial=True)

    async def find_one(
        self,
        filter: Optional[Filter] = None,
        projection: Optional[Projection] = None,
        skip: int = 0,
        sort: Optional[Sort] = None,
        allow_disk_use: Optional[bool] = None,
    ) -> T | None:
        document = await self.collection.find_one(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            skip=skip,
            sort=translate_sort(sort),
            allow_disk_use=allow_disk_use,
            session=SESSION.get(),
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    async def find_one_and_delete(
        self,
        filter: Filter,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
    ) -> T | None:
        document = await self.collection.find_one_and_delete(
            filter=translate_filter(filter),
            projection=translate_projection(projection),
            sort=translate_sort(sort),
            session=SESSION.get(),
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    @overload
    async def find_one_and_replace(
        self,
        filter: Filter,
        replacement: T,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: Literal[False] = False,
        after_document: bool = False,
    ) -> T | None: ...

    @overload
    async def find_one_and_replace(
        self,
        filter: Filter,
        replacement: T,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: Literal[True] = True,
        after_document: bool = False,
    ) -> T: ...

    async def find_one_and_replace(
        self,
        filter: Filter,
        replacement: T,
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: bool = False,
        after_document: bool = False,
    ) -> T | None:
        document = await self.collection.find_one_and_replace(
            filter=translate_filter(filter),
            replacement=replacement.to_mongo(),
            projection=translate_projection(projection),
            sort=translate_sort(sort),
            upsert=upsert,
            return_document=after_document,
            session=SESSION.get(),
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    @overload
    async def find_one_and_update(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: Literal[False] = False,
        after_document: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
    ) -> T | None: ...

    @overload
    async def find_one_and_update(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: Literal[True] = True,
        after_document: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
    ) -> T: ...

    async def find_one_and_update(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        projection: Optional[Projection] = None,
        sort: Optional[Sort] = None,
        upsert: bool = False,
        after_document: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
    ) -> T | None:
        document = await self.collection.find_one_and_update(
            filter=translate_filter(filter),
            update=update,
            projection=translate_projection(projection),
            sort=translate_sort(sort),
            upsert=upsert,
            return_document=after_document,
            array_filters=array_filters,
            session=SESSION.get(),
        )
        if document is None:
            return None
        return self.table.load(document, partial=True)

    async def delete_one(
        self,
        filter: Optional[Filter] = None,
    ) -> MongoDeleteResult:
        return await self.collection.delete_one(
            translate_filter(filter),
            session=SESSION.get(),
        )

    async def delete_many(
        self,
        filter: Optional[Filter] = None,
    ) -> MongoDeleteResult:
        return await self.collection.delete_many(
            translate_filter(filter),
            session=SESSION.get(),
        )

    async def update_one(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        upsert: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
    ) -> MongoUpdateResult:
        return await self.collection.update_one(
            translate_filter(filter),
            update,
            upsert=upsert,
            array_filters=array_filters,
            session=SESSION.get(),
        )

    async def update_many(
        self,
        filter: Filter,
        update: Mapping[str, Any] | list[Mapping[str, Any]],
        upsert: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
    ) -> MongoUpdateResult:
        return await self.collection.update_many(
            translate_filter(filter),
            update,
            upsert=upsert,
            array_filters=array_filters,
            session=SESSION.get(),
        )

    async def count_documents(
        self,
        filter: Filter,
    ) -> int:
        return await self.collection.count_documents(
            translate_filter(filter),
            session=SESSION.get(),
        )

    async def bulk_write(
        self,
        *requests: DeleteMany
        | DeleteOne
        | InsertOne[T]
        | ReplaceOne[T]
        | UpdateMany
        | UpdateOne,
        ordered: bool = True,
    ) -> MongoBlukWriteResult:
        return await self.collection.bulk_write(
            [r.to_mongo() for r in requests],
            ordered=ordered,
            session=SESSION.get(),
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
    upsert: bool = False

    def to_mongo(self) -> MongoReplaceOne:
        return MongoReplaceOne(
            translate_filter(self.filter),
            self.replacement.to_mongo(),
            upsert=self.upsert,
        )


@dataclasses.dataclass
class UpdateMany:
    filter: Filter
    update: Mapping[str, Any] | list[Mapping[str, Any]]
    upsert: bool = False
    array_filters: List[Mapping[str, Any]] | None = None

    def to_mongo(self) -> MongoUpdateMany:
        return MongoUpdateMany(
            translate_filter(self.filter),
            self.update,
            upsert=self.upsert,
            array_filters=self.array_filters,
        )


@dataclasses.dataclass
class UpdateOne:
    filter: Filter
    update: Mapping[str, Any] | list[Mapping[str, Any]]
    upsert: bool = False
    array_filters: List[Mapping[str, Any]] | None = None

    def to_mongo(self) -> MongoUpdateOne:
        return MongoUpdateOne(
            translate_filter(self.filter),
            self.update,
            upsert=self.upsert,
            array_filters=self.array_filters,
        )
