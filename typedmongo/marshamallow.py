from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from marshmallow import ValidationError, fields


class MarshamallowObjectId(fields.Field):
    def _serialize(self, value: ObjectId, attr: str | None, obj: Any, **kwargs):
        return str(value)

    def _deserialize(
        self, value: str | ObjectId | bytes, attr: str | None, data: Any, **kwargs
    ):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            raise ValidationError("Invalid ObjectId.")
