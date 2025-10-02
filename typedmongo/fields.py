from __future__ import annotations

import dataclasses
import decimal
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from bson import ObjectId
from marshmallow import fields
from typing_extensions import Self

from typedmongo.expressions import CompareMixin, HasFieldName, OrderByMixin
from typedmongo.marshamallow import (
    MarshamallowDateTime,
    MarshamallowLiteral,
    MarshamallowObjectId,
    MarshamallowUnion,
)

if TYPE_CHECKING:
    from .table import Document

TypeDocument = TypeVar("TypeDocument", bound=type["Document"])
T = TypeVar("T", bound="Document")
TypeDocumentOrAny = TypeVar("TypeDocumentOrAny", bound=type["Document"] | Any)
FieldType = TypeVar("FieldType")


@dataclasses.dataclass(eq=False, order=False, unsafe_hash=True)
class Field(Generic[FieldType], OrderByMixin, CompareMixin):
    """
    Field
    """

    default: Optional[FieldType | Callable[[], FieldType]] = dataclasses.field(
        default=None, kw_only=True
    )
    field_name: str = dataclasses.field(init=False)
    allow_none: bool = dataclasses.field(default=True, kw_only=True)
    marshamallow: fields.Field = dataclasses.field(init=False)

    def __set_name__(self, owner: type[Document], name: str) -> None:
        self._table = owner
        self._name = name

        self.field_name = name

        if not hasattr(self, "marshamallow"):
            self.marshamallow = fields.Field(required=True, allow_none=self.allow_none)
        else:
            self.marshamallow.allow_none = self.allow_none

        if self.default is not None:
            # https://github.com/marshmallow-code/marshmallow/issues/2151
            self.marshamallow.required = False
            self.marshamallow.load_default = self.default
            self.marshamallow.dump_default = self.default

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

    @property
    def field_type(self) -> type[FieldType]:
        if hasattr(self, "__field_type__"):
            return self.__field_type__  # type: ignore
        for origin_base in self.__orig_bases__:  # type: ignore
            origin_class = get_origin(origin_base)
            if isinstance(origin_class, type) and issubclass(origin_class, Field):
                self.__field_type__ = generic_type = get_args(origin_base)[0]
                return generic_type
        raise RuntimeError(f"Cannot get field type for {self}")

    def load(self, value: Any, *, partial: bool = False) -> FieldType:
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

    marshamallow: MarshamallowObjectId = dataclasses.field(
        default_factory=lambda: MarshamallowObjectId(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class LiteralField(Field[FieldType]):
    """
    Literal field
    """

    literal: type[FieldType]

    def __post_init__(self):
        self.marshamallow = MarshamallowLiteral(
            self.literal, required=True, allow_none=self.allow_none
        )

    @property
    def field_type(self) -> type[FieldType]:
        return self.literal


EnumType = TypeVar("EnumType", bound=Enum)


@dataclasses.dataclass(eq=False)
class EnumField(Field[EnumType]):
    """
    Enum field
    """

    enum: type[EnumType]

    def __post_init__(self):
        self.marshamallow = fields.Enum(
            self.enum, by_value=True, required=True, allow_none=self.allow_none
        )

    def to_mongo(self, value: EnumType) -> Any:
        return value.value

    @property
    def field_type(self) -> type[EnumType]:
        return self.enum


@dataclasses.dataclass(eq=False)
class StringField(Field[str]):
    """
    String field
    """

    marshamallow: fields.String = dataclasses.field(
        default_factory=lambda: fields.String(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class IntegerField(Field[int]):
    """
    Integer field
    """

    marshamallow: fields.Integer = dataclasses.field(
        default_factory=lambda: fields.Integer(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class FloatField(Field[float]):
    """
    Float field
    """

    marshamallow: fields.Float = dataclasses.field(
        default_factory=lambda: fields.Float(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class BooleanField(Field[bool]):
    """
    Boolean field
    """

    marshamallow: fields.Boolean = dataclasses.field(
        default_factory=lambda: fields.Boolean(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class DateTimeField(Field[datetime]):
    """
    DateTime field
    """

    marshamallow: MarshamallowDateTime = dataclasses.field(
        default_factory=lambda: MarshamallowDateTime(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class DecimalField(Field[decimal.Decimal]):
    """
    Decimal field
    """

    marshamallow: fields.Decimal = dataclasses.field(
        default_factory=lambda: fields.Decimal(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class DictField(Field[dict]):
    """
    Dict field
    """

    marshamallow: fields.Dict = dataclasses.field(
        default_factory=lambda: fields.Dict(required=True, allow_none=True)
    )


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
        self.marshamallow = fields.Nested(
            lambda: self.schema.__schema__, required=True, allow_none=self.allow_none
        )

        def load(value: Any, *, partial: bool = False) -> T:
            return self.schema.load(value, partial=partial)

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

    @property
    def field_type(self) -> type[T]:
        return self.schema


@dataclasses.dataclass(eq=False)
class ListFieldNameProxy(Generic[TypeDocumentOrAny], OrderByMixin, CompareMixin):
    number: int | None
    prefix: HasFieldName
    t: TypeDocumentOrAny

    @property
    def field_name(self) -> str:
        if self.number is None:
            return self.prefix.field_name
        return f"{self.prefix.field_name}.{self.number}"

    def __get__(self, instance, owner) -> TypeDocumentOrAny: ...

    def __getattr__(self, name: str) -> FieldNameProxyString:
        try:
            return FieldNameProxyString(
                f"{self.field_name}.{self.t.__fields__[name].field_name}"
            )
        except KeyError:
            message = "{0} has no attribute '{1}'".format(self.t, name)
            raise AttributeError(message) from None


@dataclasses.dataclass(eq=False)
class ListField(Generic[FieldType], Field[list[FieldType]]):
    """
    List field
    """

    _: ListFieldNameProxy[type[FieldType]] = dataclasses.field(init=False)

    field: Field

    def __getitem__(self, index: int) -> type[FieldType]:
        return ListFieldNameProxy(index, self, self.field.field_type)  # type: ignore

    def __post_init__(self):
        self._ = ListFieldNameProxy(None, self, self.field.field_type)

        self.marshamallow = fields.List(
            self.field.marshamallow, required=True, allow_none=self.allow_none
        )

        if isinstance(self.field, (EmbeddedField, UnionField)):
            self.marshamallow = fields.List(self.field.marshamallow)

            def load(value: Any, *, partial: bool = False) -> list[FieldType]:
                return [self.field.load(item, partial=partial) for item in value]

            def dump(value: list[FieldType]) -> list[dict[str, Any]]:
                return [self.field.dump(item) for item in value]

            def to_mongo(value: list[FieldType]) -> list[dict[str, Any]]:
                return [self.field.to_mongo(item) for item in value]

            self.load = load
            self.dump = dump
            self.to_mongo = to_mongo

    def __set_name__(self, owner: type[Document], name: str) -> None:
        if isinstance(self.field, EmbeddedField):
            self.field.schema.__lazy_init_fields__()
        return super().__set_name__(owner, name)

    @property
    def field_type(self) -> type[list[FieldType]]:
        return list[self.field.field_type]


@dataclasses.dataclass(eq=False)
class UnionField(Field[FieldType]):
    union: type[FieldType]

    def __post_init__(self):
        self.marshamallow = MarshamallowUnion(
            [type_to_field(arg) for arg in get_args(self.union)],  # type: ignore
            required=True,
            allow_none=self.allow_none,
        )

    def __set_name__(self, owner: type[Document], name: str) -> None:
        for arg in get_args(self.union):
            type_to_field(arg).__set_name__(owner, name)
        return super().__set_name__(owner, name)

    @property
    def field_type(self) -> type[FieldType]:
        return self.union


def type_to_field(type_: type) -> Field[Any]:
    from .table import Document

    if type_ is str:
        return StringField()
    if type_ is int:
        return IntegerField()
    if type_ is float:
        return FloatField()
    if type_ is bool:
        return BooleanField()
    if type_ is dict:
        return DictField()
    if type_ is datetime:
        return DateTimeField()
    if type_ is decimal.Decimal:
        return DecimalField()
    if type_ is ObjectId:
        return ObjectIdField()
    if isinstance(type_, type) and issubclass(type_, Enum):
        return EnumField(type_)
    if isinstance(type_, type) and issubclass(type_, Document):
        return EmbeddedField(type_)
    origin = get_origin(type_)
    if origin is list:
        return ListField(type_to_field(get_args(type_)[0]))
    if origin is Union or origin is UnionType:
        return UnionField(type_)
    raise ValueError(f"Cannot convert type {type_} to field")
