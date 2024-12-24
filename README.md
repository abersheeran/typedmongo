# Typed Mongo

A production-ready modern Python MongoDB ODM

In addition to synchronous mode, you can use asynchronous mode, just export from `typedmongo.asyncio`.

## Install

```bash
pip install typedmongo
```

## Usage

Usage examples trump all usage documentation. So please look at the Example below first.

<details markdown="1">
<summary>Example</summary>

```python
import datetime
from typing import Literal

from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import typedmongo.asyncio as mongo


class Wallet(mongo.Document):
    balance: mongo.DecimalField


class User(mongo.MongoDocument):
    name: mongo.StringField
    gender: mongo.LiteralField[Literal["m", "f"]]
    age: mongo.IntegerField
    tags: mongo.ListField[str]
    wallet: mongo.EmbeddedField[Wallet]
    created_at: mongo.DateTimeField = mongo.DateTimeField(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    children: mongo.ListField[User]
    extra: mongo.DictField = mongo.DictField(default=dict)


async def main():
    await mongo.initial_collections(
        MongoClient().mongo,
        User,
    )

    # Insert one document
    document_id = await User.objects.insert_one(
        User.load(
            {
                "name": "Aber",
                "gender": "m",
                "age": 18,
                "tags": ["a", "b"],
                "wallet": {"balance": 100},
                "children": [],
            },
        )
    )

    # Find one document
    user = await User.objects.find_one(User._id == document_id, sort=[+User.age])

    # Update one document
    update_result = await User.objects.update_one(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e", "r"]}}
    )

    # Delete one document
    delete_result = await User.objects.delete_one(User._id == document_id)

    # Find one and update
    user = await User.objects.find_one_and_update(
        User._id == document_id, {"$set": {"tags": ["a", "b", "e"]}}
    )

    # Find one and replace
    user = await User.objects.find_one_and_replace(
        User._id == document_id,
        User.load({"name": "Aber", "age": 0}),
        after_document=True,
    )

    # Find one and delete
    user = await User.objects.find_one_and_delete(User._id == document_id)

    # Find many documents and sort
    users = [user async for user in User.objects.find(User.age == 18, sort=[-User.age])]

    # Update many documents
    update_result = await User.objects.update_many(
        User.wallet._.balance == Decimal("100"), {"$inc": {"wallet.balance": 10}}
    )

    # Count documents
    await User.objects.count_documents(User.age >= 0)

    # Bulk write operations
    await User.objects.bulk_write(
        mongo.DeleteOne(User._id == 0),
        mongo.DeleteMany(User.age < 18),
        mongo.InsertOne(User.load({"name": "InsertOne"}, partial=True)),
        mongo.ReplaceOne(User.name == "Aber", User.load({}, partial=True)),
        mongo.UpdateMany({}, {"$set": {"age": 25}}),
        mongo.UpdateMany(User.name == "Yue", {"$set": {"name": "yue"}}),
    )
```

</details>

### Document

Note: The `Document` must be initialized with `initial_collections` before it can be used.

- `Document.load`: Load data from dict to instance, and validate the data.
- `Document.dump`: Dump the instance to jsonable dict.

#### Collection Name

`Document.__collection_name__`: Normally, subclasses of Document will generate a collection_name based on the Class Name, but if you want to customize it, you can set `__collection_name__` when defining it.

```python
class APIKey(mongo.Document):
    __collection_name__ = "api_key"
```

#### Raw Collection

If you want to use functions such as `aggregate`, you can access pymongo's original `collection` object through `Document.objects.collection`.

```python
Document.objects.collection.aggregate([
    {"$group": {"_id": "$field", "count": {"$sum": 1}}}
])
```

### Field

- `ObjectIdField`
- `StringField`
- `IntegerField`
- `DecimalField`
- `DateTimeField`
- `DictField`
- `EmbeddedField`
- `ListField`
- `LiteralField`
- `UnionField`
- `EnumField`

### Conditional expressions

If you want to use conditional expressions with methods like aggregate, you can call `expression.compile()` to get a mongo expression.

```python
Document.objects.collection.aggregate([
    {"$match": (Document.age >= 18).compile()},
    {"$group": {"_id": "$field", "count": {"$sum": 1}}},
])
```

#### Comparison expressions

- `Document.field == value`
- `Document.field != value`
- `Document.field > value`
- `Document.field >= value`
- `Document.field < value`
- `Document.field <= value`

#### Logical expressions

- `(Document.field == value) & (Document.field == value)`
- `(Document.field == value) | (Document.field == value)`
- `~(Document.field == value)`
- `~((Document.field == value) & (Document.field == value))`
- `~((Document.field == value) | (Document.field == value))`

#### `RawExpression`

Sometime, you maybe need use raw query, you can use `RawExpression` to do that.

```python
from typedmongo.asyncio import RawExpression
# Or `from typedmongo import RawExpression`

User.objects.find(RawExpression({"field_name": {"$mongo_command": value}}) & User.age > 18)
```

### Sort expressions

- `+Document.field`: Ascending
- `-Document.field`: Descending

```python
User.objects.find(..., sort=[+User.age, -User.name])
```

## Objects

- `Document.objects`: The object manager of the `Document`.
  - `collection`: The collection of the `Document`.
  - `use_session`: Use session for the operations. (Use `contextvars`, so you don't need to pass the session to the function parameters)
  - `use_transaction`: Use transaction for the operations.
  - `insert_one`: Insert one document.
  - `insert_many`: Insert many documents.
  - `find`: Find many documents.
  - `find_one`: Find one document.
  - `find_one_and_update`: Find one and update.
  - `find_one_and_replace`: Find one and replace.
  - `find_one_and_delete`: Find one and delete.
  - `delete_one`: Delete one document.
  - `delete_many`: Delete many documents.
  - `update_one`: Update one document.
  - `update_many`: Update many documents.
  - `count_documents`: Count documents.
  - `bulk_write`: Bulk write operations.
