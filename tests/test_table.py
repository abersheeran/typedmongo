from __future__ import annotations

import pytest

from typedmongo import Table, fields
from typedmongo.expressions import Expression


class Wallet(Table):
    balance = fields.FloatField()


class User(Table):
    name: fields.StringField
    age: fields.IntegerField
    tags: fields.ListField[str]
    wallet: fields.EmbeddedField[Wallet]
    children: fields.ListField[User]


User.__lazy_init_fields__()


@pytest.mark.parametrize(
    "expression, repr_str",
    [
        (
            User.name == "Aber",
            "CompareExpression(field=name, operator='==', arg='Aber')",
        ),
        (
            User.age >= 18,
            "CompareExpression(field=age, operator='>=', arg=18)",
        ),
        (
            User.tags == "a",
            "CompareExpression(field=tags, operator='==', arg='a')",
        ),
        (
            User.tags[0] == "0",
            "CompareExpression(field=tags.0, operator='==', arg='0')",
        ),
        (
            User.wallet._.balance > 1,
            "CompareExpression(field=wallet.balance, operator='>', arg=1)",
        ),
        (
            User.children[0].name == "Yue",
            "CompareExpression(field=children.0.name, operator='==', arg='Yue')",
        ),
        (
            User.children._.age >= 18,
            "CompareExpression(field=children.age, operator='>=', arg=18)",
        ),
    ],
)
def test_expression(expression, repr_str):
    assert isinstance(expression, Expression)
    assert repr(expression) == repr_str
