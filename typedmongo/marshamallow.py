from bson import ObjectId
from bson.errors import InvalidId
from marshmallow import ValidationError, fields


class MarshamallowObjectId(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            raise ValidationError("Invalid ObjectId.")
