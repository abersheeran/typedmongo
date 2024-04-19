from __future__ import annotations

import dataclasses
from typing import Any, Literal, Protocol


class HasFieldName(Protocol):
    field_name: str


class Expression:
    """
    Base class for all expressions.
    """

    def __invert__(self) -> Expression:
        """
        ~self
        """
        if isinstance(self, NotExpression):
            return self.expr
        else:
            return NotExpression(self)

    def __and__(self, other: Expression) -> CombineExpression:
        """
        self & other
        """
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("AND", self, other)

    def __rand__(self, other: Expression) -> CombineExpression:
        """
        other & self
        """
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("AND", other, self)

    def __or__(self, other: Expression) -> CombineExpression:
        """
        self | other
        """
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("OR", self, other)

    def __ror__(self, other: Expression) -> CombineExpression:
        """
        other | self
        """
        if not isinstance(other, Expression):
            return NotImplemented
        return CombineExpression("OR", other, self)


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


class ArithmeticMixin:
    def __add__(self, other: Any) -> ArithmeticExpression:
        """
        self + other
        """
        return ArithmeticExpression(self, "+", other)

    def __radd__(self, other: Any) -> ArithmeticExpression:
        """
        other + self
        """
        return ArithmeticExpression(other, "+", self)

    def __sub__(self, other: Any) -> ArithmeticExpression:
        """
        self - other
        """
        return ArithmeticExpression(self, "-", other)

    def __rsub__(self, other: Any) -> ArithmeticExpression:
        """
        other - self
        """
        return ArithmeticExpression(other, "-", self)

    def __mul__(self, other: Any) -> ArithmeticExpression:
        """
        self * other
        """
        return ArithmeticExpression(self, "*", other)

    def __rmul__(self, other: Any) -> ArithmeticExpression:
        """
        other * self
        """
        return ArithmeticExpression(other, "*", self)

    def __truediv__(self, other: Any) -> ArithmeticExpression:
        """
        self / other
        """
        return ArithmeticExpression(self, "/", other)

    def __rtruediv__(self, other: Any) -> ArithmeticExpression:
        """
        other / self
        """
        return ArithmeticExpression(other, "/", self)

    def __mod__(self, other: Any) -> ArithmeticExpression:
        """
        self % other
        """
        return ArithmeticExpression(self, "%", other)

    def __rmod__(self, other: Any) -> ArithmeticExpression:
        """
        other % self
        """
        return ArithmeticExpression(other, "%", self)


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
class NotExpression(Expression):
    expr: Expression


@dataclasses.dataclass(repr=False)
class CombineExpression(Expression, BetterReprMixin):
    operator: Literal["AND", "OR"]
    left: Expression
    right: Expression


@dataclasses.dataclass(repr=False)
class CompareExpression(Expression, BetterReprMixin):
    field: HasFieldName
    operator: Literal[">=", "<=", ">", "<", "==", "!="]
    arg: Any


@dataclasses.dataclass(repr=False)
class ArithmeticExpression(Expression, BetterReprMixin):
    left: Any
    operator: Literal["-", "+", "*", "/", "%"]
    right: Any


class OrderByMixin(HasFieldName):
    def __neg__(self) -> OrderBy:
        """
        -self
        """
        return OrderBy(self, "DESC")

    def __pos__(self) -> OrderBy:
        """
        +self
        """
        return OrderBy(self, "ASC")


@dataclasses.dataclass(repr=False)
class OrderBy(BetterReprMixin):
    field: HasFieldName
    order: Literal["DESC", "ASC"]
