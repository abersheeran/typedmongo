from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal, Protocol, overload

from typing_extensions import Self

if TYPE_CHECKING:
    # Solve TypeError: Cannot create a consistent method resolution
    class HasFieldName(Protocol):
        field_name: str
else:

    class HasFieldName:
        field_name: str


class Expression:
    """
    Base class for all expressions.
    """

    def __invert__(self) -> Expression:
        """
        ~self
        """
        match self:
            case NotExpression(expr):
                return expr
            case CombineExpression("AND", left, right):
                return CombineExpression("OR", ~left, ~right)
            case CombineExpression("OR", left, right):
                return CombineExpression("AND", ~left, ~right)
            case CompareExpression():
                return NotExpression(self)
            case _:
                raise NotImplementedError

    @overload
    def __and__(self, other: None) -> Self: ...

    @overload
    def __and__(self, other: Expression) -> CombineExpression: ...

    def __and__(self, other):
        """
        self & other
        """
        if other is None:
            return self
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("AND", self, other)

    @overload
    def __rand__(self, other: None) -> Self: ...

    @overload
    def __rand__(self, other: Expression) -> CombineExpression: ...

    def __rand__(self, other):
        """
        other & self
        """
        if other is None:
            return self
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("AND", other, self)

    @overload
    def __or__(self, other: None) -> Self: ...

    @overload
    def __or__(self, other: Expression) -> CombineExpression: ...

    def __or__(self, other):
        """
        self | other
        """
        if other is None:
            return self
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("OR", self, other)

    @overload
    def __ror__(self, other: None) -> Self: ...

    @overload
    def __ror__(self, other: Expression) -> CombineExpression: ...

    def __ror__(self, other):
        """
        other | self
        """
        if other is None:
            return self
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("OR", other, self)

    def compile(self) -> dict[str, Any]:
        return compile_expression(self)


@dataclasses.dataclass
class RawExpression(Expression):
    raw: dict[str, Any]


class CompareMixin(HasFieldName):
    def __eq__(self, other: Any) -> CompareExpression:
        """
        self == other
        """
        return CompareExpression(self, "==", other)

    def __ne__(self, other: Any) -> CompareExpression:
        """
        self != other
        """
        return CompareExpression(self, "!=", other)

    def __lt__(self, other: Any) -> CompareExpression:
        """
        self < other
        """
        return CompareExpression(self, "<", other)

    def __le__(self, other: Any) -> CompareExpression:
        """
        self <= other
        """
        return CompareExpression(self, "<=", other)

    def __gt__(self, other: Any) -> CompareExpression:
        """
        self > other
        """
        return CompareExpression(self, ">", other)

    def __ge__(self, other: Any) -> CompareExpression:
        """
        self >= other
        """
        return CompareExpression(self, ">=", other)


@dataclasses.dataclass(repr=False)
class BetterReprMixin:
    def __repr__(self) -> str:
        names = self.__dataclass_fields__.keys()

        attrs_str = []
        for name in names:
            v = getattr(self, name)
            if hasattr(v, "field_name"):
                repr_str = getattr(v, "field_name")
            else:
                repr_str = repr(v)
            attrs_str.append(f"{name}={repr_str}")
        return f"{self.__class__.__name__}({', '.join(attrs_str)})"


@dataclasses.dataclass
class CombineExpression(Expression):
    operator: Literal["AND", "OR"]
    left: Expression
    right: Expression


@dataclasses.dataclass(repr=False)
class CompareExpression(Expression, BetterReprMixin):
    field: HasFieldName
    operator: Literal[">=", "<=", ">", "<", "==", "!="]
    arg: Any


@dataclasses.dataclass
class NotExpression(Expression):
    expr: CompareExpression


def compile_expression(expr: Expression) -> dict[str, Any]:
    match expr:
        case RawExpression(raw):
            return raw
        case CompareExpression(field, "==", arg):
            return {field.field_name: arg}
        case CompareExpression(field, "!=", arg):
            return {field.field_name: {"$ne": arg}}
        case CompareExpression(field, ">", arg):
            return {field.field_name: {"$gt": arg}}
        case CompareExpression(field, ">=", arg):
            return {field.field_name: {"$gte": arg}}
        case CompareExpression(field, "<", arg):
            return {field.field_name: {"$lt": arg}}
        case CompareExpression(field, "<=", arg):
            return {field.field_name: {"$lte": arg}}
        case CombineExpression("AND", left, right):
            return {"$and": [compile_expression(left), compile_expression(right)]}
        case CombineExpression("OR", left, right):
            return {"$or": [compile_expression(left), compile_expression(right)]}
        case NotExpression(inner):
            return {
                inner.field.field_name: {
                    "$not": compile_expression(inner).pop(inner.field.field_name)
                }
            }
        case _:
            raise NotImplementedError(f"Unsupported expression: {expr}")


class OrderByMixin(HasFieldName):
    def __neg__(self) -> OrderBy:
        """
        -self
        """
        return OrderBy(self, -1)

    def __pos__(self) -> OrderBy:
        """
        +self
        """
        return OrderBy(self, +1)


@dataclasses.dataclass(repr=False)
class OrderBy(BetterReprMixin):
    field: HasFieldName
    order: Literal[-1, +1]
