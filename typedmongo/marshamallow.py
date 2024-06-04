from datetime import datetime
from typing import Any, get_args

from bson import ObjectId
from bson.errors import InvalidId
from marshmallow import ValidationError, fields


class MarshamallowObjectId(fields.Field):
    def _serialize(self, value: ObjectId, attr: str | None, obj: Any, **kwargs) -> str:
        return str(value)

    def _deserialize(
        self, value: str | ObjectId | bytes, attr: str | None, data: Any, **kwargs
    ) -> ObjectId:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            raise ValidationError("Invalid ObjectId.")


class MarshamallowDateTime(fields.DateTime):
    def _deserialize(
        self, value: str | datetime, attr: str | None, data: Any, **kwargs
    ) -> datetime:
        if isinstance(value, datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)


class MarshamallowLiteral(fields.Field):
    def __init__(self, literal: Any, **kwargs):
        self.enum = get_args(literal)
        super().__init__(**kwargs)

    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs) -> Any:
        if value not in self.enum:
            raise ValidationError(f"Value must be {self.enum}")
        return value
