import dataclasses
import enum

import pytest

from typedmongo.expressions import (
    CombineExpression,
    CompareExpression,
    CompareMixin,
    NotExpression,
    RawExpression,
)


@dataclasses.dataclass(eq=False)
class Field(CompareMixin):
    field_name: str


class TestEnum(enum.Enum):
    TEST = "test"


field = Field("name")


@pytest.mark.parametrize(
    "expression, expected, compiled",
    [
        (field >= 18, CompareExpression(field, ">=", 18), {"name": {"$gte": 18}}),
        (field > 18, CompareExpression(field, ">", 18), {"name": {"$gt": 18}}),
        (field < 18, CompareExpression(field, "<", 18), {"name": {"$lt": 18}}),
        (field <= 18, CompareExpression(field, "<=", 18), {"name": {"$lte": 18}}),
        (field == "Aber", CompareExpression(field, "==", "Aber"), {"name": "Aber"}),
        (
            field != "Aber",
            CompareExpression(field, "!=", "Aber"),
            {"name": {"$ne": "Aber"}},
        ),
        (
            ~(field == "Aber"),
            NotExpression(CompareExpression(field, "==", "Aber")),
            {"name": {"$not": "Aber"}},
        ),
        (
            (field > 18) & (field < 35),
            CombineExpression(
                "AND",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
            {"$and": [{"name": {"$gt": 18}}, {"name": {"$lt": 35}}]},
        ),
        (
            (field > 18) | (field < 35),
            CombineExpression(
                "OR",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
            {"$or": [{"name": {"$gt": 18}}, {"name": {"$lt": 35}}]},
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
            {
                "$or": [
                    {
                        "$and": [{"name": {"$gt": 18}}, {"name": {"$lt": 35}}],
                    },
                    {"name": 35},
                ]
            },
        ),
        (
            ~((field > 18) & (field < 35)),
            CombineExpression(
                "OR",
                NotExpression(CompareExpression(field, ">", 18)),
                NotExpression(CompareExpression(field, "<", 35)),
            ),
            {
                "$or": [
                    {"name": {"$not": {"$gt": 18}}},
                    {"name": {"$not": {"$lt": 35}}},
                ]
            },
        ),
        (
            ~((field > 18) | (field < 35)),
            CombineExpression(
                "AND",
                NotExpression(CompareExpression(field, ">", 18)),
                NotExpression(CompareExpression(field, "<", 35)),
            ),
            {
                "$and": [
                    {"name": {"$not": {"$gt": 18}}},
                    {"name": {"$not": {"$lt": 35}}},
                ]
            },
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
            {
                "$and": [
                    {
                        "$or": [
                            {"name": {"$not": {"$gt": 18}}},
                            {"name": {"$not": {"$lt": 35}}},
                        ]
                    },
                    {"name": {"$not": 35}},
                ]
            },
        ),
        (
            ~~((field > 18) & (field < 35)),
            CombineExpression(
                "AND",
                CompareExpression(field, ">", 18),
                CompareExpression(field, "<", 35),
            ),
            {"$and": [{"name": {"$gt": 18}}, {"name": {"$lt": 35}}]},
        ),
        (
            None & (field > 18),
            CompareExpression(field, ">", 18),
            {"name": {"$gt": 18}},
        ),
        (
            (field > 18) & None,
            CompareExpression(field, ">", 18),
            {"name": {"$gt": 18}},
        ),
        (
            RawExpression({"name": "Aber"}) | (field > 18),
            CombineExpression(
                "OR",
                RawExpression({"name": "Aber"}),
                CompareExpression(field, ">", 18),
            ),
            {"$or": [{"name": "Aber"}, {"name": {"$gt": 18}}]},
        ),
        (
            field == TestEnum.TEST,
            CompareExpression(field, "==", TestEnum.TEST),
            {"name": "test"},
        ),
    ],
)
def test_compile_expressions(expression, expected, compiled):
    assert expression == expected
    assert expression.compile() == compiled
