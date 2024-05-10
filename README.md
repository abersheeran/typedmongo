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
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import typedmongo.asyncio as mongo


class Wallet(mongo.Table):
    balance: mongo.DecimalField


class User(mongo.MongoTable):
    name: mongo.StringField
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

### Table

- `Table.load`: Load data from dict to instance, and validate the data.
- `Table.dump`: Dump the instance to jsonable dict.

### Field

- `ObjectIdField`
- `StringField`
- `IntegerField`
- `DecimalField`
- `DateTimeField`
- `DictField`
- `EmbeddedField`
- `ListField`

### Conditional expressions

#### Comparison expressions

- `Table.field == value`
- `Table.field != value`
- `Table.field > value`
- `Table.field >= value`
- `Table.field < value`
- `Table.field <= value`

#### Logical expressions

- `(Table.field == value) & (Table.field == value)`
- `(Table.field == value) | (Table.field == value)`
- `~(Table.field == value)`
- `~((Table.field == value) & (Table.field == value))`
- `~((Table.field == value) | (Table.field == value))`

### Sort expressions

- `+Table.field`: Ascending
- `-Table.field`: Descending

## Objects

- `Table.objects`: The object manager of the table.
  - `collection`: The collection of the table.
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
