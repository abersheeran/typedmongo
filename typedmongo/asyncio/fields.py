from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING, Any, Self, get_args, get_origin, overload

from bson import ObjectId
from bson.errors import InvalidId
from marshmallow import ValidationError, fields

from typedmongo.expressions import CompareMixin, HasFieldName, OrderByMixin

if TYPE_CHECKING:
    from .table import Table


@dataclasses.dataclass(eq=False)
class Field[FieldType](OrderByMixin, CompareMixin):
    """
    Field
    """

    field_name: str = dataclasses.field(init=False)
    marshamallow: fields.Field = dataclasses.field(init=False)

    def __set_name__(self, owner: type[Table], name: str) -> None:
        self._table = owner
        self._name = name

        self.field_name = name

        if not hasattr(self, "marshamallow"):
            self.marshamallow = fields.Field(required=True)

    @overload
    def __get__(self: Self, instance: None, cls: type) -> Self:
        ...

    @overload
    def __get__(self: Self, instance: object, cls: type) -> FieldType:
        ...

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

    @classmethod
    def get_field_type(cls) -> type[FieldType]:
        if hasattr(cls, "__field_type__"):
            return cls.__field_type__  # type: ignore
        for origin_base in cls.__orig_bases__:  # type: ignore
            origin_class = get_origin(origin_base)
            if isinstance(origin_class, type) and issubclass(origin_class, Field):
                cls.__field_type__ = generic_type = get_args(origin_base)[0]
                return generic_type
        raise RuntimeError(f"Cannot get field type for {cls}")

    def load(self, value: Any, *, partial: bool = False) -> FieldType:
        return value

    def to_mongo(self, value: FieldType) -> Any:
        return value


class _ObjectIdField(fields.Field):
    def _serialize(self, value: ObjectId, attr, obj, **kwargs):
        return str(value)

    def _deserialize(self, value: str, attr, data, **kwargs):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            raise ValidationError("Invalid ObjectId.")


@dataclasses.dataclass(eq=False)
class ObjectIdField(Field[ObjectId]):
    """
    ObjectId field
    """

    marshamallow: fields.Field = _ObjectIdField(required=True)


@dataclasses.dataclass(eq=False)
class StringField(Field[str]):
    """
    String field
    """

    marshamallow: fields.Field = fields.String(required=True)


@dataclasses.dataclass(eq=False)
class IntegerField(Field[int]):
    """
    Integer field
    """

    marshamallow: fields.Field = fields.Integer(required=True)


@dataclasses.dataclass(eq=False)
class FloatField(Field[float]):
    """
    Float field
    """

    marshamallow: fields.Field = fields.Float(required=True)


@dataclasses.dataclass(eq=False)
class BooleanField(Field[bool]):
    """
    Boolean field
    """

    marshamallow: fields.Field = fields.Boolean(required=True)


@dataclasses.dataclass(eq=False)
class DateTimeField(Field[datetime]):
    """
    DateTime field
    """

    marshamallow: fields.Field = fields.DateTime(required=True)


@dataclasses.dataclass
class FieldNameProxy[T: type[Table]]:
    prefix: HasFieldName
    t: T

    def __get__(self, instance, owner) -> T:
        ...

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
class EmbeddedField[T: Table](Field[T]):
    """
    Embedded field
    """

    _: FieldNameProxy[type[T]] = dataclasses.field(init=False)

    schema: type[T]

    def __post_init__(self):
        self._ = FieldNameProxy(self, self.schema)
        self.marshamallow = fields.Nested(self.schema.__schema__)

        def load(value: Any, *, partial: bool = False) -> T:
            return self.schema.load(value, partial=partial)

        self.load = load


@dataclasses.dataclass(eq=False)
class ListFieldNameProxy[T: type[Table] | Any](OrderByMixin, CompareMixin):
    number: int | None
    prefix: HasFieldName
    t: T

    @property
    def field_name(self) -> str:
        if self.number is None:
            return self.prefix.field_name
        return f"{self.prefix.field_name}.{self.number}"

    def __get__(self, instance, owner) -> T:
        ...

    def __getattr__(self, name: str) -> FieldNameProxyString:
        try:
            return FieldNameProxyString(
                f"{self.field_name}.{self.t.__fields__[name].field_name}"
            )
        except KeyError:
            message = "{0} has no attribute '{1}'".format(self.t, name)
            raise AttributeError(message) from None


@dataclasses.dataclass(eq=False)
class ListField[T](Field[list[T]]):
    """
    List field
    """

    _: ListFieldNameProxy[type[T]] = dataclasses.field(init=False)

    type_or_schema: type[T]

    def __getitem__(self, index: int) -> type[T]:
        return ListFieldNameProxy(index, self, self.type_or_schema)  # type: ignore

    def __post_init__(self):
        self._ = ListFieldNameProxy(None, self, self.type_or_schema)

        from .table import Table

        if issubclass(self.type_or_schema, Table):
            self.marshamallow = fields.List(
                fields.Nested(self.type_or_schema.__schema__)
            )

            def load(value: Any, *, partial: bool = False) -> list[T]:
                return [
                    self.type_or_schema.load(item, partial=partial)  # type: ignore
                    for item in value
                ]

            self.load = load
        else:
            self.marshamallow = fields.List(
                {
                    int: fields.Integer(required=True),
                    float: fields.Float(required=True),
                    bool: fields.Boolean(required=True),
                    str: fields.String(required=True),
                    datetime: fields.DateTime(required=True),
                }[self.type_or_schema]  # type: ignore
            )
