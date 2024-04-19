from copy import deepcopy
from functools import reduce
from typing import TYPE_CHECKING, Any, Sequence

from marshmallow.schema import Schema, SchemaMeta

from .exceptions import TableDefineError
from .fields import Field, ObjectIdField
from .indexes import Index


def snake_case(name: str) -> str:
    """
    convert "SomeWords" to "some_words"
    """
    return "".join(
        "_" + char.lower() if char.isupper() and i > 0 else char.lower()
        for i, char in enumerate(name)
    )


class TableMetaClass(SchemaMeta):
    if TYPE_CHECKING:
        __abstract__: bool
        __client__: Any
        __collection__: Any
        __fields__: dict[str, Field]
        __indexes__: Sequence[Index]

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

        namespace.setdefault("__abstract__", False)

        namespace.setdefault("__indexes__", ())

        def merge_dict(*d):
            new = dict()
            for _ in reversed(d):
                new.update(_)
            return new

        # merge bases' `__fields__` to `__fields__`
        namespace["__fields__"] = reduce(
            lambda _initial, _item: {**_item, **_initial},
            reversed([getattr(base, "__fields__", {}) for base in bases]),
            {
                name: value
                for name, value in namespace.items()
                if isinstance(value, Field)
            },
        )

        return super().__new__(cls, name, bases, namespace)

    def __init__(self, cls_name, bases, namespace) -> None:
        self.__alias__ = ""
        for name, attr in namespace.items():
            if callable(getattr(attr, "__set_name__", None)):
                attr.__set_name__(self, name)
        super().__init__(cls_name, bases, namespace)

    def __call__(self, **kwargs):
        instance = super().__call__()
        instance._from_db = False

        # Store updated fields in the instance
        instance.update_fields = []

        if instance.__abstract__:
            raise RuntimeError(
                "The class {} cannot be instantiated, because it's __abstract__ is True.".format(
                    self.__name__
                )
            )

        for name, value in kwargs.items():
            setattr(instance, name, value)

        # Clear initial fields
        instance.update_fields.clear()

        return instance

    def __setattr__(self, name, value):
        if name == "__abstract__":
            raise AttributeError(
                "Can't modify the `__abstract__` attribute dynamically."
            )
        return super().__setattr__(name, value)

    def _create_from_db(self, **kwargs):
        mapping = {field.field_name: name for name, field in self.__fields__.items()}
        model = self(**{mapping[k]: v for k, v in kwargs.items()})
        model._from_db = True
        return model


class Table(Schema, metaclass=TableMetaClass):
    __abstract__: bool = True

    if TYPE_CHECKING:
        _from_db: bool

        update_fields: list[str]

    _id = ObjectIdField()

    def dict(self, copy: bool = False) -> dict[str, Any]:
        dictionary = {k: v for k, v in self.__dict__.items() if k in self.__fields__}
        return deepcopy(dictionary) if copy else dictionary
