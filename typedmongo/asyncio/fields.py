from __future__ import annotations

import dataclasses
import decimal
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
    get_args,
    get_origin,
    overload,
)

from bson import ObjectId
from typing_extensions import Self

from typedmongo.expressions import CompareMixin, HasFieldName, OrderByMixin
from typedmongo.marshamallow import (
    MarshamallowDateTime,
    MarshamallowLiteral,
    MarshamallowObjectId,
)

if TYPE_CHECKING:
    from .table import Document

TypeDocument = TypeVar("TypeDocument", bound=type["Document"])
T = TypeVar("T", bound="Document")
TypeDocumentOrAny = TypeVar("TypeDocumentOrAny", bound=type["Document"] | Any)
FieldType = TypeVar("FieldType")


@dataclasses.dataclass
class FieldParamters(Generic[FieldType]):
    default: Optional[FieldType | Callable[[], FieldType]] = dataclasses.field(
        default=None, kw_only=True
    )


@dataclasses.dataclass(eq=False, order=False, unsafe_hash=True)
class Field(Generic[FieldType], OrderByMixin, CompareMixin):
    """
    Field
    """

    default: Optional[FieldType | Callable[[], FieldType]] = dataclasses.field(
        default=None, kw_only=True
    )
    field_name: str = dataclasses.field(init=False)

    def __set_name__(self, owner: type[Document], name: str) -> None:
        self._table = owner
        self._name = name

        self.field_name = name

    @overload
    def __get__(self: Self, instance: None, cls: type) -> Self: ...

    @overload
    def __get__(self: Self, instance: object, cls: type) -> FieldType: ...

    def __get__(self, instance, cls):
        if instance is None:  # Call from class
            return self

        try:
            return instance.__dict__[self._name]
        except KeyError:
            message = "{0} has no attribute '{1}'".format(instance, self._name)
            raise AttributeError(message) from None

    def __set__(self, instance: Document, value: Any) -> None:
        instance.__dict__[self._name] = value

    def __delete__(self, instance: Document) -> None:
        try:
            del instance.__dict__[self._name]
        except KeyError:
            message = "{0} has no attribute '{1}'".format(instance, self._name)
            raise AttributeError(message)

    def get_field_type(self) -> type[FieldType]:
        if hasattr(self, "__field_type__"):
            return self.__field_type__  # type: ignore
        for origin_base in self.__orig_bases__:  # type: ignore
            origin_class = get_origin(origin_base)
            if isinstance(origin_class, type) and issubclass(origin_class, Field):
                self.__field_type__ = generic_type = get_args(origin_base)[0]
                return generic_type
        raise RuntimeError(f"Cannot get field type for {self}")

    def load(self, value: Any) -> FieldType:
        return value

    def dump(self, value: FieldType) -> Any:
        return value

    def to_mongo(self, value: FieldType) -> Any:
        return value


@dataclasses.dataclass(eq=False)
class ObjectIdField(Field[ObjectId]):
    """
    ObjectId field
    """


LiteralField = Field


@dataclasses.dataclass(eq=False)
class StringField(Field[str]):
    """
    String field
    """


@dataclasses.dataclass(eq=False)
class IntegerField(Field[int]):
    """
    Integer field
    """


@dataclasses.dataclass(eq=False)
class FloatField(Field[float]):
    """
    Float field
    """


@dataclasses.dataclass(eq=False)
class BooleanField(Field[bool]):
    """
    Boolean field
    """


@dataclasses.dataclass(eq=False)
class DateTimeField(Field[datetime]):
    """
    DateTime field
    """

    marshamallow: MarshamallowDateTime = dataclasses.field(
        default_factory=lambda: MarshamallowDateTime(required=True, allow_none=False)
    )


@dataclasses.dataclass(eq=False)
class DecimalField(Field[decimal.Decimal]):
    """
    Decimal field
    """


@dataclasses.dataclass(eq=False)
class DictField(Field[dict]):
    """
    Dict field
    """


@dataclasses.dataclass
class FieldNameProxy(Generic[TypeDocument]):
    prefix: HasFieldName
    t: TypeDocument

    def __get__(self, instance, owner) -> TypeDocument: ...

    def __getattr__(self, name: str) -> FieldNameProxyString:
        try:
            return FieldNameProxyString(
                f"{self.prefix.field_name}.{self.t.__fields__[name].field_name}"
            )
        except KeyError:
            message = "{0} has no attribute '{1}'".format(self.t, name)
            raise AttributeError(message) from None


@dataclasses.dataclass(eq=False)
class FieldNameProxyString(OrderByMixin, CompareMixin):
    field_name: str


@dataclasses.dataclass(eq=False)
class EmbeddedField(Generic[T], Field[T]):
    """
    Embedded field
    """

    _: FieldNameProxy[type[T]] = dataclasses.field(init=False)

    schema: type[T]

    def __post_init__(self):
        self._ = FieldNameProxy(self, self.schema)

        def load(value: Any) -> T:
            return self.schema.load(value)

        def dump(value: T) -> dict[str, Any]:
            return self.schema.dump(value)

        def to_mongo(value: T) -> dict[str, Any]:
            return self.schema.to_mongo(value)

        self.load = load
        self.dump = dump
        self.to_mongo = to_mongo

    def __set_name__(self, owner: type[Document], name: str) -> None:
        if not issubclass(self.schema, owner):
            self.schema.__lazy_init_fields__()
        return super().__set_name__(owner, name)
