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
from marshmallow import fields
from typing_extensions import Self

from typedmongo.expressions import CompareMixin, HasFieldName, OrderByMixin
from typedmongo.marshamallow import MarshamallowDateTime, MarshamallowObjectId

if TYPE_CHECKING:
    from .table import Table

TypeTable = TypeVar("TypeTable", bound=type["Table"])
T = TypeVar("T", bound="Table")
TypeTableOrAny = TypeVar("TypeTableOrAny", bound=type["Table"] | Any)
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
    marshamallow: fields.Field = dataclasses.field(init=False)

    def __set_name__(self, owner: type[Table], name: str) -> None:
        self._table = owner
        self._name = name

        self.field_name = name

        if not hasattr(self, "marshamallow"):
            self.marshamallow = fields.Field(required=True, allow_none=False)

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

    def __set__(self, instance: Table, value: Any) -> None:
        instance.__dict__[self._name] = value

    def __delete__(self, instance: Table) -> None:
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

    marshamallow: fields.Field = MarshamallowObjectId(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class StringField(Field[str]):
    """
    String field
    """

    marshamallow: fields.Field = fields.String(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class IntegerField(Field[int]):
    """
    Integer field
    """

    marshamallow: fields.Field = fields.Integer(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class FloatField(Field[float]):
    """
    Float field
    """

    marshamallow: fields.Field = fields.Float(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class BooleanField(Field[bool]):
    """
    Boolean field
    """

    marshamallow: fields.Field = fields.Boolean(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class DateTimeField(Field[datetime]):
    """
    DateTime field
    """

    marshamallow: fields.Field = MarshamallowDateTime(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class DecimalField(Field[decimal.Decimal]):
    """
    Decimal field
    """

    marshamallow: fields.Field = fields.Decimal(required=True, allow_none=False)


@dataclasses.dataclass(eq=False)
class DictField(Field[dict]):
    """
    Dict field
    """

    marshamallow: fields.Field = fields.Dict(required=True, allow_none=False)


@dataclasses.dataclass
class FieldNameProxy(Generic[TypeTable]):
    prefix: HasFieldName
    t: TypeTable

    def __get__(self, instance, owner) -> TypeTable: ...

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
        self.marshamallow = fields.Nested(lambda: self.schema.__schema__)

        def load(value: Any, *, partial: bool = False) -> T:
            return self.schema.load(value, partial=partial)

        def dump(value: T) -> dict[str, Any]:
            return self.schema.dump(value)

        def to_mongo(value: T) -> dict[str, Any]:
            return self.schema.to_mongo(value)

        self.load = load
        self.dump = dump
        self.to_mongo = to_mongo

    def __set_name__(self, owner: type[Table], name: str) -> None:
        if not issubclass(self.schema, owner):
            self.schema.__lazy_init_fields__()
        return super().__set_name__(owner, name)

    def get_field_type(self) -> type[T]:
        return self.schema


@dataclasses.dataclass(eq=False)
class ListFieldNameProxy(Generic[TypeTableOrAny], OrderByMixin, CompareMixin):
    number: int | None
    prefix: HasFieldName
    t: TypeTableOrAny

    @property
    def field_name(self) -> str:
        if self.number is None:
            return self.prefix.field_name
        return f"{self.prefix.field_name}.{self.number}"

    def __get__(self, instance, owner) -> TypeTableOrAny: ...

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

    field: Field[FieldType]

    def __getitem__(self, index: int) -> type[FieldType]:
        return ListFieldNameProxy(index, self, self.field.get_field_type())  # type: ignore

    def __post_init__(self):
        self._ = ListFieldNameProxy(None, self, self.field.get_field_type())  # type: ignore

        self.marshamallow = fields.List(self.field.marshamallow)  # type: ignore

        if isinstance(self.field, EmbeddedField):
            self.marshamallow = fields.List(self.field.marshamallow)

            def load(value: Any, *, partial: bool = False) -> list[FieldType]:
                return [self.field.load(item, partial=partial) for item in value]  # type: ignore

            def dump(value: list[FieldType]) -> list[dict[str, Any]]:
                return [self.field.dump(item) for item in value]  # type: ignore

            def to_mongo(value: list[FieldType]) -> list[dict[str, Any]]:
                return [self.field.to_mongo(item) for item in value]  # type: ignore

            self.load = load
            self.dump = dump
            self.to_mongo = to_mongo

    def get_field_type(self) -> type[list[FieldType]]:
        return list[self.field.get_field_type()]  # type: ignore


def type_to_field(type_: type) -> Field:
    from .table import Table

    if type_ is str:
        return StringField()
    if type_ is int:
        return IntegerField()
    if type_ is float:
        return FloatField()
    if type_ is bool:
        return BooleanField()
    if type_ is datetime:
        return DateTimeField()
    if type_ is decimal.Decimal:
        return DecimalField()
    if type_ is ObjectId:
        return ObjectIdField()
    if issubclass(type_, Table):
        return EmbeddedField(type_)
    if get_origin(type_) is list:
        return ListField(type_to_field(get_args(type_)[0]))
    raise ValueError(f"Cannot convert type {type_} to field")
