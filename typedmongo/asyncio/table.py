import dataclasses
import inspect
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    Optional,
    Sequence,
    get_args,
    get_origin,
)

from marshmallow import Schema
from pymongo import IndexModel
from typing_extensions import Self, dataclass_transform

from typedmongo.exceptions import TableDefineError

from .client import Manager
from .fields import Field, ListField, type_to_field


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
    keys: (
        Field
        | Sequence[tuple[Field, int | str | Mapping[str, Any]]]
        | Mapping[Field, Any]
    )

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

        parameters = dataclasses.asdict(self)
        del parameters["keys"]
        if parameters["partialFilterExpression"] is None:
            del parameters["partialFilterExpression"]
        if parameters["expireAfterSeconds"] is None:
            del parameters["expireAfterSeconds"]
        return IndexModel(keys=keys, **parameters)


@dataclass_transform(eq_default=False, kw_only_default=True)
class TableMetaClass(type):
    if TYPE_CHECKING:
        __abstract__: bool
        __database__: Any
        __collection_name__: str
        __collection__: Any
        __pfields__: dict[str, Field]
        __sfields__: dict[str, Field]
        __fields_loaded__: bool
        __fields__: dict[str, Field]
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

        if "__fields__" in namespace:  # Clear __fields__ to avoid conflict
            del namespace["__fields__"]
        namespace["__fields_loaded__"] = False

        namespace["__sfields__"] = {
            name: value for name, value in namespace.items() if isinstance(value, Field)
        }
        # merge bases' `__fields__` to `__pfields__`
        namespace["__pfields__"] = reduce(
            lambda _initial, _item: {**_item, **_initial},
            reversed(
                [
                    base.__lazy_init_fields__()
                    for base in bases
                    if isinstance(base, TableMetaClass)
                ]
            ),
            {},
        )

        if "__create_schema__" not in namespace:
            for base in bases:
                create_schema = base.__create_schema__
            namespace["__create_schema__"] = create_schema

        return super().__new__(cls, name, bases, namespace)

    def __lazy_init_fields__(cls) -> dict[str, Field]:
        if cls.__fields_loaded__:
            return cls.__fields__

        fields = {
            **{
                name: value()
                for name, value in inspect.get_annotations(cls, eval_str=True).items()
                if isinstance(value, type) and issubclass(value, Field)
            },
            **{
                name: origin_class(type_to_field(get_args(value)[0]))
                if issubclass(origin_class, ListField)
                else origin_class(*get_args(value))
                for name, value in inspect.get_annotations(cls, eval_str=True).items()
                if (origin_class := get_origin(value))
                and isinstance(origin_class, type)
                and issubclass(origin_class, Field)
            },
            **cls.__sfields__,
        }
        cls.__fields__ = {**cls.__pfields__, **fields}
        cls.__fields_loaded__ = True

        for name, field in fields.items():
            setattr(cls, name, field)
            field.__set_name__(cls, name)

        cls.__schema__ = cls.__create_schema__(cls.__name__, cls.__fields__)
        return fields

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
    __abstract__ = True

    objects = Manager()

    def __repr__(self) -> str:
        return "{class_name}({fields})".format(
            class_name=self.__class__.__name__,
            fields=", ".join(
                f"{name}={repr(self.__dict__[name])}"
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
        """
        Load data from dict to instance, and validate the data.

        :param data: The data to load.
        :param partial: If True, allow partial data to load.
        """
        validated: dict[str, Any] = cls.__schema__.load(data=data, partial=partial)  # type: ignore
        if partial:
            # The default value would NOT be loaded when partial is True.
            # https://github.com/marshmallow-code/marshmallow/issues/2151
            for key, field in cls.__fields__.items():
                if field.default is not None:
                    default_value = field.default
                    if callable(default_value):
                        default_value = default_value()
                    validated.setdefault(key, default_value)
        loaded = {
            key: getattr(cls.__fields__[key], "load")(value, partial=partial)
            for key, value in validated.items()
        }
        return cls(**loaded)

    @classmethod
    def dump(cls, instance: Self) -> dict[str, Any]:
        """
        Dump the instance to jsonable dict.
        """
        dumped = {
            key: getattr(instance.__fields__[key], "dump")(value)
            for key, value in instance.__dict__.items()
        }
        return cls.__schema__.dump(dumped)  # type: ignore

    @classmethod
    def indexes(cls) -> list[Index]:
        return []

    def to_mongo(self) -> dict[str, Any]:
        """
        Dump the instance to dict for mongo.
        """
        return {
            key: getattr(self.__fields__[key], "to_mongo")(value)
            for key, value in self.__dict__.items()
        }
