import dataclasses

import pytest

from typedmongo.expressions import (
    CombineExpression,
    CompareExpression,
    CompareMixin,
    NotExpression,
)


@dataclasses.dataclass(eq=False)
class Field(CompareMixin):
    field_name: str


field = Field("name")


@pytest.mark.parametrize(
    "expression, expected",
    [
        (field >= 18, CompareExpression(field, ">=", 18)),
        (field > 18, CompareExpression(field, ">", 18)),
        (field < 18, CompareExpression(field, "<", 18)),
        (field <= 18, CompareExpression(field, "<=", 18)),
        (field == "Aber", CompareExpression(field, "==", "Aber")),
        (field != "Aber", CompareExpression(field, "!=", "Aber")),
        (~(field == "Aber"), NotExpression(CompareExpression(field, "==", "Aber"))),
        (
            (field > 18) & (field < 35),
            CombineExpression(
                "AND",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
        ),
        (
            (field > 18) | (field < 35),
            CombineExpression(
                "OR",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
        ),
        (
            (field > 18) & (field < 35) | (field == 35),
            CombineExpression(
                "OR",
                CombineExpression(
                    "AND",
                    CompareExpression(field, ">", 18),
                    CompareExpression(field, "<", 35),
                ),
                CompareExpression(field, "==", 35),
            ),
        ),
        (
            ~((field > 18) & (field < 35)),
            CombineExpression(
                "OR",
                NotExpression(CompareExpression(field, ">", 18)),
                NotExpression(CompareExpression(field, "<", 35)),
            ),
        ),
        (
            ~((field > 18) | (field < 35)),
            CombineExpression(
                "AND",
                NotExpression(CompareExpression(field, ">", 18)),
                NotExpression(CompareExpression(field, "<", 35)),
            ),
        ),
        (
            ~((field > 18) & (field < 35) | (field == 35)),
            CombineExpression(
                "AND",
                CombineExpression(
                    "OR",
                    NotExpression(CompareExpression(field, ">", 18)),
                    NotExpression(CompareExpression(field, "<", 35)),
                ),
                NotExpression(CompareExpression(field, "==", 35)),
            ),
        ),
        (
            ~~((field > 18) & (field < 35)),
            CombineExpression(
                "AND",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
        ),
        (
            None & (field > 18),
            CompareExpression(field, ">", 18),
        ),
    ],
)
def test_compile_expressions(expression, expected):
    assert expression == expected
