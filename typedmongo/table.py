import dataclasses
import inspect
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    Optional,
    Self,
    Sequence,
    get_args,
    get_origin,
)

from marshmallow import Schema
from pymongo import IndexModel

from typedmongo.exceptions import TableDefineError

from .client import Manager
from .fields import Field, ObjectIdField


def snake_case(name: str) -> str:
    """
    convert "SomeWords" to "some_words"
    """
    return "".join(
        "_" + char.lower() if char.isupper() and i > 0 else char.lower()
        for i, char in enumerate(name)
    )


@dataclasses.dataclass
class Index:
    keys: Field | Sequence[tuple[Field, int]] | Mapping[Field, Any]

    name: Optional[str] = None
    unique: bool = False
    background: bool = False
    sparse: bool = False
    expireAfterSeconds: Optional[int] = None
    partialFilterExpression: Optional[dict[str, Any]] = None

    def to_index_model(self) -> IndexModel:
        if isinstance(self.keys, Field):
            keys = self.keys.field_name
        elif isinstance(self.keys, Mapping):
            keys = {field.field_name: value for field, value in self.keys.items()}
        else:
            keys = [(field.field_name, value) for field, value in self.keys]

        return IndexModel(
            keys=keys,
            name=self.name,
            unique=self.unique,
            background=self.background,
            sparse=self.sparse,
            expireAfterSeconds=self.expireAfterSeconds,
            partialFilterExpression=self.partialFilterExpression,
        )


class TableMetaClass(type):
    if TYPE_CHECKING:
        __abstract__: bool
        __database__: Any
        __collection_name__: str
        __collection__: Any
        __fields__: dict[str, Field]
        __fields_loaded__: bool
        __create_schema__: Callable[[str, dict[str, Field]], Schema]
        __schema__: Schema

    def __new__(cls, name, bases, namespace):
        if "_" in name:  # check error name. e.g. Status_Info
            raise TableDefineError(
                "Table class name cannot have '_': {name}".format(name=name)
            )
        if not name[0].isupper():  # check error name. e.g. statusInfo
            raise TableDefineError(
                "Table class name must be upper letter in start: {name}".format(
                    name=name
                )
            )
        namespace.setdefault("__collection_name__", snake_case(name))
        namespace.setdefault("__abstract__", False)

        # merge bases' `__fields__` to `__fields__`
        fields = {
            name: value for name, value in namespace.items() if isinstance(value, Field)
        }
        namespace["__fields_loaded__"] = not not fields
        namespace["__fields__"] = reduce(
            lambda _initial, _item: {**_item, **_initial},
            reversed([getattr(base, "__fields__", {}) for base in bases]),
            fields,
        )

        if "__create_schema__" not in namespace:
            for base in bases:
                create_schema = base.__create_schema__
            namespace["__create_schema__"] = create_schema
        namespace["__schema__"] = namespace["__create_schema__"](
            name, namespace["__fields__"]
        )

        return super().__new__(cls, name, bases, namespace)

    def __lazy_init_fields__(cls) -> None:
        if cls.__fields_loaded__:
            return

        fields = {
            **{
                name: value()
                for name, value in inspect.get_annotations(cls, eval_str=True).items()
                if isinstance(value, type) and issubclass(value, Field)
            },
            **{
                name: origin_class(*get_args(value))
                for name, value in inspect.get_annotations(cls, eval_str=True).items()
                if (origin_class := get_origin(value))
                and isinstance(origin_class, type)
                and issubclass(origin_class, Field)
            },
        }
        for name, field in fields.items():
            setattr(cls, name, field)
            field.__set_name__(cls, name)
        cls.__fields_loaded__ = True
        cls.__fields__ = {**cls.__fields__, **fields}
        cls.__schema__ = cls.__create_schema__(cls.__name__, fields)

    def __call__(cls, **kwargs: Any):
        instance = super().__call__()

        if instance.__abstract__:
            raise RuntimeError(
                "The class {} cannot be instantiated, because it's __abstract__ is True.".format(
                    cls.__name__
                )
            )

        for name, value in kwargs.items():
            setattr(instance, name, value)

        return instance

    def __setattr__(cls, name, value):
        if name == "__abstract__":
            raise AttributeError(
                "Can't modify the `__abstract__` attribute dynamically."
            )
        return super().__setattr__(name, value)


class Table(metaclass=TableMetaClass):
    __abstract__: bool = True

    _id = ObjectIdField()

    objects = Manager()

    def __repr__(self) -> str:
        return "{class_name}({fields})".format(
            class_name=self.__class__.__name__,
            fields=", ".join(
                f"{name}={self.__dict__[name]}"
                for name, _ in self.__fields__.items()
                if name in self.__dict__
            ),
        )

    @staticmethod
    def __create_schema__(name: str, fields: dict[str, Field]) -> Schema:
        schema_class = Schema.from_dict(
            {name: field.marshamallow for name, field in fields.items()}, name=name
        )
        return schema_class(unknown="exclude")

    @classmethod
    def load(
        cls: type[Self], data: Mapping[str, Any], *, partial: bool = False
    ) -> Self:
        validated = cls.__schema__.load(data=data, partial=partial)
        loaded = {
            key: getattr(cls.__fields__[key], "load")(value, partial=partial)
            for key, value in validated.items()  # type: ignore
        }
        return cls(**loaded)

    def to_mongo(self) -> dict[str, Any]:
        return {
            key: getattr(self.__fields__[key], "to_mongo")(value)
            for key, value in self.__dict__.items()
            if key in self.__fields__
        }
