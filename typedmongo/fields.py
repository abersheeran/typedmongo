from __future__ import annotations

from datetime import datetime
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Self,
    get_args,
    get_origin,
    overload,
    TYPE_CHECKING,
)

from bson import ObjectId
from marshmallow import fields
from marshmallow.utils import missing as missing_

from .expressions import OrderByMixin, CompareMixin, ArithmeticMixin

if TYPE_CHECKING:
    from .table import Table


class Field[FieldType](fields.Field, OrderByMixin, CompareMixin, ArithmeticMixin):
    def __init__(
        self,
        *,
        load_default: Any = missing_,
        missing: Any = missing_,
        dump_default: Any = missing_,
        default: Any = missing_,
        data_key: str | None = None,
        attribute: str | None = None,
        validate: None | Callable[[Any], Any] | Iterable[Callable[[Any], Any]] = None,
        required: bool = False,
        allow_none: bool | None = None,
        load_only: bool = False,
        dump_only: bool = False,
        error_messages: dict[str, str] | None = None,
        metadata: Mapping[str, Any] | None = None,
        **additional_metadata,
    ) -> None:
        super().__init__(
            load_default=load_default,
            missing=missing,
            dump_default=dump_default,
            default=default,
            data_key=data_key,
            attribute=attribute,
            validate=validate,
            required=required,
            allow_none=allow_none,
            load_only=load_only,
            dump_only=dump_only,
            error_messages=error_messages,
            metadata=metadata,
            **additional_metadata,
        )

    def __set_name__(self, owner: type[Table], name: str) -> None:
        self._table = owner
        self._name = name

        if not self.field_name:
            self.field_name = name

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
        if value != instance.__dict__.get(self._name):
            instance.update_fields.append(self._name)
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


class ObjectIdField(Field[ObjectId]):
    """
    ObjectId field
    """


class StringField(Field[str], fields.String):
    """
    String field
    """


class IntegerField(Field[int]):
    """
    Integer field
    """


class FloatField(Field[float]):
    """
    Float field
    """


class BooleanField(Field[bool]):
    """
    Boolean field
    """


class DateTimeField(Field[datetime]):
    """
    DateTime field
    """


class ListField[T](Field[list[T]]):
    """
    List field
    """

    type_or_schema: type[T]
