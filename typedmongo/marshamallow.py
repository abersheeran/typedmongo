from datetime import datetime
from typing import Any, List, get_args

import marshmallow.error_store
import marshmallow.exceptions
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


class MarshamallowUnion(fields.Field):
    def __init__(self, fields: List[Any], **kwargs: Any):
        self._candidate_fields = fields
        super().__init__(**kwargs)

    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs):
        fields = self._candidate_fields
        for candidate_field in fields:
            try:
                return candidate_field.dump(value)
            except ValidationError:
                pass

        raise ValidationError(
            f"Unable to serialize value {value} with any of the candidate fields"
        )

    def _deserialize(
        self, value: Any, attr: str, data: Any, partial: bool = False, **kwargs: Any
    ):
        errors = []
        for candidate_field in self._candidate_fields:
            try:
                return candidate_field.load(value, partial=partial)
            except marshmallow.exceptions.ValidationError as exc:
                errors.append(exc.messages)
        raise ValidationError(message=errors, field_name=attr)
