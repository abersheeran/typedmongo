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
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)
from typing import (
    Optional as TypingOptional,
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
MarshamallowFieldType = TypeVar("MarshamallowFieldType", bound=fields.Field)


@dataclasses.dataclass(eq=False, order=False, unsafe_hash=True)
class Field(Generic[FieldType, MarshamallowFieldType], OrderByMixin, CompareMixin):
    """
    Field
    """

    default: TypingOptional[FieldType | Callable[[], FieldType]] = dataclasses.field(
        default=None, kw_only=True
    )
    field_name: str = dataclasses.field(init=False)
    allow_none: bool = dataclasses.field(default=True, kw_only=True)
    marshamallow: MarshamallowFieldType = dataclasses.field(init=False)

    def __set_name__(self, owner: type[Document], name: str) -> None:
        self._table = owner
        self._name = name

        self.field_name = name

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
class ObjectIdField(Field[ObjectId, MarshamallowObjectId]):
    """
    ObjectId field
    """

    marshamallow: MarshamallowObjectId = dataclasses.field(
        default_factory=lambda: MarshamallowObjectId(required=True, allow_none=True)
    )

    def dump(self, value: ObjectId) -> Any:
        return str(value)


@dataclasses.dataclass(eq=False)
class LiteralField(Field[FieldType, MarshamallowLiteral]):
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
class EnumField(Field[EnumType, fields.Enum]):
    """
    Enum field
    """

    enum: type[EnumType]

    def __post_init__(self):
        self.marshamallow = fields.Enum(
            self.enum, by_value=True, required=True, allow_none=self.allow_none
        )

    def dump(self, value: EnumType) -> Any:
        return value.value

    def to_mongo(self, value: EnumType) -> Any:
        return value.value

    @property
    def field_type(self) -> type[EnumType]:
        return self.enum


@dataclasses.dataclass(eq=False)
class StringField(Field[str, fields.String]):
    """
    String field
    """

    marshamallow: fields.String = dataclasses.field(
        default_factory=lambda: fields.String(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class IntegerField(Field[int, fields.Integer]):
    """
    Integer field
    """

    marshamallow: fields.Integer = dataclasses.field(
        default_factory=lambda: fields.Integer(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class FloatField(Field[float, fields.Float]):
    """
    Float field
    """

    marshamallow: fields.Float = dataclasses.field(
        default_factory=lambda: fields.Float(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class BooleanField(Field[bool, fields.Boolean]):
    """
    Boolean field
    """

    marshamallow: fields.Boolean = dataclasses.field(
        default_factory=lambda: fields.Boolean(required=True, allow_none=True)
    )


@dataclasses.dataclass(eq=False)
class DateTimeField(Field[datetime, MarshamallowDateTime]):
    """
    DateTime field
    """

    marshamallow: MarshamallowDateTime = dataclasses.field(
        default_factory=lambda: MarshamallowDateTime(required=True, allow_none=True)
    )

    def dump(self, value: datetime) -> Any:
        return value.isoformat(timespec="microseconds")


@dataclasses.dataclass(eq=False)
class DecimalField(Field[decimal.Decimal, fields.Decimal]):
    """
    Decimal field
    """

    marshamallow: fields.Decimal = dataclasses.field(
        default_factory=lambda: fields.Decimal(required=True, allow_none=True)
    )

    def dump(self, value: decimal.Decimal) -> Any:
        return str(value)


@dataclasses.dataclass(eq=False)
class DictField(Field[dict, fields.Dict]):
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
class EmbeddedField(Generic[T], Field[T, fields.Nested]):
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
    def field_name(self) -> str:  # type: ignore
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
class ListField(Generic[FieldType], Field[list[FieldType], fields.List]):
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
class UnionField(Field[FieldType, MarshamallowUnion]):
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

    def dump(self, value: FieldType) -> Any:
        if hasattr(value, "dump"):
            return value.dump()  # type: ignore
        return value

    def to_mongo(self, value: FieldType) -> Any:
        if hasattr(value, "to_mongo"):
            return value.to_mongo()  # type: ignore
        return value


@dataclasses.dataclass(eq=False)
class OptionalField(Generic[FieldType], Field[FieldType | None, Any]):
    """
    Optional field that defaults to None and allows None values.

    Usage:
        class User(Document):
            name: StringField  # Required
            nickname: OptionalField[str]  # Optional, defaults to None
            wallet: OptionalField[Wallet]  # Optional embedded document
            tags: OptionalField[list[str]]  # Optional list

    Behavior:
        - Construction: user = User(name="Alice") -> nickname is None
        - Load (non-partial): User.load({"name": "Bob"}) -> nickname is None
        - Load (partial): User.load({"name": "Charlie"}, partial=True) -> nickname is None

    Difference from allow_none=True:
        - Regular fields with allow_none=True still require a value (or explicit default)
        - OptionalField[T] fields automatically default to None if missing,
          in both partial and non-partial loads
    """

    inner_type: type[FieldType]
    inner_field: Field = dataclasses.field(init=False, repr=False)

    def __post_init__(self):
        # Derive inner field from type
        inner = type_to_field(self.inner_type)

        # Configure inner field
        inner.allow_none = True

        # Store inner field (can't use assignment due to descriptor protocol)
        setattr(self, "inner_field", inner)

        # Use inner field's marshamallow, but mark as not required (we have a default)
        self.marshamallow = inner.marshamallow
        self.marshamallow.required = False
        self.marshamallow.load_default = lambda: None
        self.marshamallow.dump_default = lambda: None

        # Set allow_none and default at wrapper level
        self.allow_none = True
        self.default = lambda: None

    def __set_name__(self, owner: type[Document], name: str) -> None:
        # Bind both wrapper and inner field
        self._table = owner
        self._name = name
        self.field_name = name

        # Also bind inner field - access via object.__getattribute__ to bypass descriptor
        inner = object.__getattribute__(self, "inner_field")
        inner.__set_name__(owner, name)

    @property
    def field_type(self) -> type[FieldType | None]:
        inner = object.__getattribute__(self, "inner_field")
        return inner.field_type | None  # type: ignore

    def load(self, value: Any, *, partial: bool = False) -> FieldType | None:
        if value is None:
            return None
        inner = object.__getattribute__(self, "inner_field")
        return inner.load(value, partial=partial)

    def dump(self, value: FieldType | None) -> Any:
        if value is None:
            return None
        inner = object.__getattribute__(self, "inner_field")
        return inner.dump(value)

    def to_mongo(self, value: FieldType | None) -> Any:
        if value is None:
            return None
        inner = object.__getattribute__(self, "inner_field")
        return inner.to_mongo(value)

    # Forward nested query proxies
    def __getattr__(self, name: str) -> Any:
        # Forward to inner field for nested query support
        # Don't forward these internal attributes
        if name in (
            "field_name",
            "inner_field",
            "inner_type",
        ):
            return object.__getattribute__(self, name)
        # Forward everything else to inner field (including "_" for nested queries)
        inner = object.__getattribute__(self, "inner_field")
        if hasattr(inner, name):
            return getattr(inner, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __getitem__(self, index: int) -> Any:
        # Forward list indexing to inner field (for OptionalField[list[T]])
        inner = object.__getattribute__(self, "inner_field")
        if hasattr(inner, "__getitem__"):
            return inner[index]
        raise TypeError(f"'{type(inner).__name__}' object is not subscriptable")

    @classmethod
    def __class_getitem__(cls, item: type) -> type["OptionalField"]:
        """
        Support OptionalField[T] syntax via PEP 560.

        This method is called when you write OptionalField[str], OptionalField[int], etc.
        """
        # Validate that item is not a Field type
        if isinstance(item, type) and issubclass(item, Field):
            raise TypeError(
                f"mongo.OptionalField[T] expects a Python value type, not a Field type. "
                f"Use mongo.OptionalField[{item.__name__.replace('Field', '').lower()}] instead."
            )

        # Create a new class that inherits from OptionalField directly
        # Note: We inherit from cls (which is OptionalField) directly, not cls[item]
        class _ParameterizedOptional(cls):  # type: ignore
            def __init__(self, **kwargs):
                if kwargs:
                    raise TypeError(
                        f"mongo.OptionalField[{item}] cannot be instantiated with arguments. "
                        f"It's automatically configured."
                    )
                super().__init__(inner_type=item)

        _ParameterizedOptional.__name__ = (
            f"OptionalField[{getattr(item, '__name__', str(item))}]"
        )
        _ParameterizedOptional.__qualname__ = (
            f"OptionalField[{getattr(item, '__name__', str(item))}]"
        )

        return _ParameterizedOptional


def type_to_field(type_: type) -> Field[Any, Any]:
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
    if origin is Literal:
        return LiteralField(type_)
    if origin is list:
        return ListField(type_to_field(get_args(type_)[0]))
    if origin is Union or origin is UnionType:
        return UnionField(type_)
    raise ValueError(f"Cannot convert type {type_} to field")
