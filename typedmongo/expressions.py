from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .fields import Field


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


class CompareMixin:
    def __lt__(self, other) -> CompareExpression:
        """
        self < other
        """
        return CompareExpression(self, "<", other)

    def __le__(self, other) -> CompareExpression:
        """
        self <= other
        """
        return CompareExpression(self, "<=", other)

    def __eq__(self, other) -> CompareExpression:
        """
        self == other
        """
        return CompareExpression(self, "==", other)

    def __ne__(self, other) -> CompareExpression:
        """
        self != other
        """
        return CompareExpression(self, "!=", other)

    def __gt__(self, other) -> CompareExpression:
        """
        self > other
        """
        return CompareExpression(self, ">", other)

    def __ge__(self, other) -> CompareExpression:
        """
        self >= other
        """
        return CompareExpression(self, ">=", other)


class ArithmeticMixin:
    def __add__(self, other) -> ArithmeticExpression:
        """
        self + other
        """
        return ArithmeticExpression(self, "+", other)

    def __radd__(self, other) -> ArithmeticExpression:
        """
        other + self
        """
        return ArithmeticExpression(other, "+", self)

    def __sub__(self, other) -> ArithmeticExpression:
        """
        self - other
        """
        return ArithmeticExpression(self, "-", other)

    def __rsub__(self, other) -> ArithmeticExpression:
        """
        other - self
        """
        return ArithmeticExpression(other, "-", self)

    def __mul__(self, other) -> ArithmeticExpression:
        """
        self * other
        """
        return ArithmeticExpression(self, "*", other)

    def __rmul__(self, other) -> ArithmeticExpression:
        """
        other * self
        """
        return ArithmeticExpression(other, "*", self)

    def __truediv__(self, other) -> ArithmeticExpression:
        """
        self / other
        """
        return ArithmeticExpression(self, "/", other)

    def __rtruediv__(self, other) -> ArithmeticExpression:
        """
        other / self
        """
        return ArithmeticExpression(other, "/", self)

    def __mod__(self, other) -> ArithmeticExpression:
        """
        self % other
        """
        return ArithmeticExpression(self, "%", other)

    def __rmod__(self, other) -> ArithmeticExpression:
        """
        other % self
        """
        return ArithmeticExpression(other, "%", self)


@dataclasses.dataclass
class NotExpression(Expression):
    expr: Expression


@dataclasses.dataclass
class CombineExpression(Expression):
    operator: Literal["AND", "OR"]
    left: Expression
    right: Expression


@dataclasses.dataclass
class CompareExpression(Expression):
    field: Field
    operator: Literal[">=", "<=", ">", "<", "==", "!="]
    arg: Any


@dataclasses.dataclass
class ArithmeticExpression(Expression):
    left: Any
    operator: Literal["-", "+", "*", "/", "%"]
    right: Any


class OrderByMixin:
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


@dataclasses.dataclass
class OrderBy:
    field: Field
    order: Literal["DESC", "ASC"]
