from typedmongo.table import Table
from typedmongo import fields


class User(Table):
    name = fields.StringField()
    age = fields.IntegerField()
    email = fields.StringField()


user = User().load({"name": "John", "age": 20, "email": "123"})
print(user)


from marshmallow import Schema, fields


class UserSchema(Schema):
    name = fields.String()
    age = fields.Integer()
    email = fields.String()


user = UserSchema().load({"name": "John", "age": 20, "email": "123"})
