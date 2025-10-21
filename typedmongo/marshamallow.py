from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, get_args

from bson import ObjectId
from bson.errors import InvalidId
from marshmallow import ValidationError, fields

if TYPE_CHECKING:
    from .fields import Field


class MarshamallowObjectId(fields.Field):
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


class MarshamallowUnion(fields.Field):
    def __init__(self, fields: List[Field[Any]], **kwargs: Any):
        self._candidate_fields = fields
        self._candidate_fields_map = {field.field_type: field for field in fields}
        super().__init__(**kwargs)

    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any):
        errors = []
        try_field = self._candidate_fields_map.get(type(value))
        if try_field:
            return try_field.load(
                try_field.marshamallow.deserialize(value, attr, data, **kwargs)
            )

        for candidate_field in self._candidate_fields:
            try:
                return candidate_field.load(
                    candidate_field.marshamallow.deserialize(
                        value, attr, data, **kwargs
                    )
                )
            except ValidationError as exc:
                errors.append(exc.messages)
        raise ValidationError(message=errors, field_name=attr if attr is not None else "")
