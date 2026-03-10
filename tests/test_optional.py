from __future__ import annotations

import datetime
import enum
from decimal import Decimal
from typing import Literal

import pytest

import typedmongo as mongo


class Wallet(mongo.Document):
    balance: mongo.DecimalField
    currency: mongo.StringField = mongo.StringField(default="USD")


class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(mongo.Document):
    # Required fields
    name: mongo.StringField

    # Optional fields with different types
    nickname: mongo.OptionalField[str]
    age: mongo.OptionalField[int]
    bio: mongo.OptionalField[str]
    wallet: mongo.OptionalField[Wallet]
    tags: mongo.OptionalField[list[str]]
    gender: mongo.OptionalField[Literal["m", "f", "other"]]
    status: mongo.OptionalField[Status]
    metadata: mongo.OptionalField[dict]


User.__lazy_init_fields__()


class TestOptionalBasics:
    """Test basic Optional field functionality."""

    def test_optional_field_default_none(self):
        """Optional fields should default to None in normal construction."""
        user = User(name="Alice")
        assert user.name == "Alice"
        assert user.nickname is None
        assert user.age is None
        assert user.bio is None
        assert user.wallet is None
        assert user.tags is None
        assert user.gender is None
        assert user.status is None
        assert user.metadata is None

    def test_optional_field_explicit_value(self):
        """Can set explicit values for Optional fields."""
        user = User(
            name="Bob",
            nickname="Bobby",
            age=25,
            bio="Developer",
            tags=["python", "mongodb"],
            gender="m",
            metadata={"key": "value"},
        )
        assert user.name == "Bob"
        assert user.nickname == "Bobby"
        assert user.age == 25
        assert user.bio == "Developer"
        assert user.tags == ["python", "mongodb"]
        assert user.gender == "m"
        assert user.metadata == {"key": "value"}

    def test_optional_field_explicit_none(self):
        """Can explicitly set Optional fields to None."""
        user = User(name="Charlie", nickname=None, age=None)
        assert user.name == "Charlie"
        assert user.nickname is None
        assert user.age is None


class TestOptionalLoad:
    """Test Optional field load behavior."""

    def test_load_without_optional_fields(self):
        """load() without partial should default missing Optional fields to None."""
        data = {"name": "Alice"}
        user = User.load(data)
        assert user.name == "Alice"
        assert user.nickname is None
        assert user.age is None
        assert user.bio is None
        assert user.wallet is None
        assert user.tags is None
        assert user.gender is None
        assert user.status is None
        assert user.metadata is None

    def test_load_with_optional_fields(self):
        """load() with Optional fields should load them correctly."""
        data = {
            "name": "Bob",
            "nickname": "Bobby",
            "age": 25,
            "bio": "Developer",
            "tags": ["python", "mongodb"],
            "gender": "m",
            "status": "active",
            "metadata": {"key": "value"},
        }
        user = User.load(data)
        assert user.name == "Bob"
        assert user.nickname == "Bobby"
        assert user.age == 25
        assert user.bio == "Developer"
        assert user.tags == ["python", "mongodb"]
        assert user.gender == "m"
        assert user.status == Status.ACTIVE
        assert user.metadata == {"key": "value"}

    def test_load_with_explicit_none(self):
        """load() should handle explicit None values."""
        data = {"name": "Charlie", "nickname": None, "age": None}
        user = User.load(data)
        assert user.name == "Charlie"
        assert user.nickname is None
        assert user.age is None

    def test_load_partial_without_optional_fields(self):
        """load(partial=True) should NOT default missing Optional fields."""
        data = {"name": "Alice"}
        user = User.load(data, partial=True)
        assert user.name == "Alice"
        # Optional fields should NOT be set in partial mode
        assert not hasattr(user, "nickname")
        assert not hasattr(user, "age")
        assert not hasattr(user, "bio")
        assert not hasattr(user, "wallet")
        assert not hasattr(user, "tags")
        assert not hasattr(user, "gender")
        assert not hasattr(user, "status")
        assert not hasattr(user, "metadata")

    def test_load_partial_with_optional_fields(self):
        """load(partial=True) with Optional fields should load them."""
        data = {"name": "Bob", "nickname": "Bobby", "age": 25}
        user = User.load(data, partial=True)
        assert user.name == "Bob"
        assert user.nickname == "Bobby"
        assert user.age == 25
        # Other Optional fields should NOT be set
        assert not hasattr(user, "bio")
        assert not hasattr(user, "wallet")

    def test_load_partial_with_explicit_none(self):
        """load(partial=True) should handle explicit None values."""
        data = {"name": "Charlie", "nickname": None}
        user = User.load(data, partial=True)
        assert user.name == "Charlie"
        assert user.nickname is None
        # Check that the attribute exists (was set to None)
        assert hasattr(user, "nickname")


class TestOptionalDump:
    """Test Optional field dump behavior."""

    def test_dump_with_none_values(self):
        """dump() should include None values for Optional fields."""
        user = User(name="Alice")
        dumped = user.dump()
        assert dumped["name"] == "Alice"
        assert dumped["nickname"] is None
        assert dumped["age"] is None
        assert dumped["bio"] is None
        assert dumped["wallet"] is None
        assert dumped["tags"] is None
        assert dumped["gender"] is None
        assert dumped["status"] is None
        assert dumped["metadata"] is None

    def test_dump_with_values(self):
        """dump() should correctly dump Optional fields with values."""
        user = User(
            name="Bob",
            nickname="Bobby",
            age=25,
            tags=["python"],
            gender="m",
            status=Status.ACTIVE,
            metadata={"key": "value"},
        )
        dumped = user.dump()
        assert dumped["name"] == "Bob"
        assert dumped["nickname"] == "Bobby"
        assert dumped["age"] == 25
        assert dumped["tags"] == ["python"]
        assert dumped["gender"] == "m"
        assert dumped["status"] == "active"
        assert dumped["metadata"] == {"key": "value"}

    def test_dump_partial_object(self):
        """dump() should only include set attributes."""
        data = {"name": "Alice", "nickname": "Ali"}
        user = User.load(data, partial=True)
        dumped = user.dump()
        assert dumped == {"name": "Alice", "nickname": "Ali"}


class TestOptionalToMongo:
    """Test Optional field to_mongo behavior."""

    def test_to_mongo_with_none_values(self):
        """to_mongo() should include None values."""
        user = User(name="Alice")
        mongo_doc = user.to_mongo()
        assert mongo_doc["name"] == "Alice"
        assert mongo_doc["nickname"] is None
        assert mongo_doc["age"] is None

    def test_to_mongo_with_values(self):
        """to_mongo() should correctly convert Optional fields."""
        user = User(
            name="Bob",
            nickname="Bobby",
            age=25,
            status=Status.ACTIVE,
        )
        mongo_doc = user.to_mongo()
        assert mongo_doc["name"] == "Bob"
        assert mongo_doc["nickname"] == "Bobby"
        assert mongo_doc["age"] == 25
        assert mongo_doc["status"] == "active"


class TestOptionalEmbedded:
    """Test Optional with embedded documents."""

    def test_optional_embedded_none(self):
        """Optional embedded document defaults to None."""
        user = User(name="Alice")
        assert user.wallet is None

    def test_optional_embedded_with_value(self):
        """Can set Optional embedded document."""
        wallet = Wallet(balance=Decimal("100.50"))
        user = User(name="Bob", wallet=wallet)
        assert user.wallet is not None
        assert user.wallet.balance == Decimal("100.50")
        assert user.wallet.currency == "USD"

    def test_optional_embedded_load(self):
        """load() should correctly handle Optional embedded documents."""
        data = {
            "name": "Charlie",
            "wallet": {"balance": "200.75", "currency": "EUR"},
        }
        user = User.load(data)
        assert user.wallet is not None
        assert user.wallet.balance == Decimal("200.75")
        assert user.wallet.currency == "EUR"

    def test_optional_embedded_dump(self):
        """dump() should correctly handle Optional embedded documents."""
        wallet = Wallet(balance=Decimal("100.50"))
        user = User(name="Dave", wallet=wallet)
        dumped = user.dump()
        assert dumped["wallet"] == {"balance": "100.50", "currency": "USD"}

    def test_optional_embedded_nested_query(self):
        """Should support nested queries on Optional embedded fields."""
        # This tests that the `_` proxy is forwarded correctly
        assert hasattr(User.wallet, "_")
        field_proxy = User.wallet._.balance
        assert field_proxy.field_name == "wallet.balance"


class TestOptionalList:
    """Test Optional with list fields."""

    def test_optional_list_none(self):
        """Optional list defaults to None (not empty list)."""
        user = User(name="Alice")
        assert user.tags is None

    def test_optional_list_with_value(self):
        """Can set Optional list."""
        user = User(name="Bob", tags=["python", "mongodb"])
        assert user.tags == ["python", "mongodb"]

    def test_optional_list_empty(self):
        """Can set Optional list to empty list."""
        user = User(name="Charlie", tags=[])
        assert user.tags == []

    def test_optional_list_load(self):
        """load() should correctly handle Optional lists."""
        data = {"name": "Dave", "tags": ["java", "postgres"]}
        user = User.load(data)
        assert user.tags == ["java", "postgres"]

    def test_optional_list_indexing(self):
        """Should support list indexing on Optional list fields."""
        # This tests that the `[]` operator is forwarded correctly
        field_proxy = User.tags[0]
        assert field_proxy.field_name == "tags.0"


class TestOptionalErrors:
    """Test error cases for Optional."""

    def test_optional_with_field_type_raises_error(self):
        """Using Optional[FieldType] should raise clear error."""
        with pytest.raises(TypeError, match="expects a Python value type"):

            class BadUser(mongo.Document):
                name: mongo.OptionalField[mongo.StringField]

            BadUser.__lazy_init_fields__()

    def test_optional_annotation_with_explicit_field_raises_error(self):
        """Using Optional annotation with explicit field should raise error."""
        from typedmongo.exceptions import DocumentDefineError

        with pytest.raises(DocumentDefineError, match="mongo.OptionalField"):

            class BadUser2(mongo.Document):
                name: mongo.OptionalField[str] = mongo.StringField()

            BadUser2.__lazy_init_fields__()

    def test_optional_cannot_instantiate_directly(self):
        """Cannot instantiate Optional class directly without inner_type."""
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'inner_type'"):
            mongo.OptionalField()


class TestOptionalWithRegularDefaults:
    """Test that regular fields with defaults still work."""

    def test_regular_field_with_default_still_works(self):
        """Regular fields with default should still work."""
        wallet = Wallet(balance=Decimal("100"))
        assert wallet.balance == Decimal("100")
        assert wallet.currency == "USD"

    def test_regular_field_partial_load(self):
        """Regular fields with default in partial load."""
        data = {"balance": "50.00"}
        wallet = Wallet.load(data, partial=True)
        assert wallet.balance == Decimal("50.00")
        # Regular field with default should still apply in partial mode
        assert wallet.currency == "USD"


class TestOptionalRepr:
    """Test Optional field representation."""

    def test_repr_with_none_values(self):
        """repr should show None for unset Optional fields."""
        user = User(name="Alice")
        repr_str = repr(user)
        assert "name='Alice'" in repr_str
        assert "nickname=None" in repr_str

    def test_repr_with_values(self):
        """repr should show values for set Optional fields."""
        user = User(name="Bob", nickname="Bobby", age=25)
        repr_str = repr(user)
        assert "name='Bob'" in repr_str
        assert "nickname='Bobby'" in repr_str
        assert "age=25" in repr_str

    def test_repr_partial(self):
        """repr should only show set fields in partial objects."""
        data = {"name": "Charlie", "age": 30}
        user = User.load(data, partial=True)
        repr_str = repr(user)
        assert "name='Charlie'" in repr_str
        assert "age=30" in repr_str
        # Unset Optional fields should not appear
        assert "nickname" not in repr_str


class TestOptionalEquality:
    """Test Optional field equality."""

    def test_equality_with_same_values(self):
        """Users with same values should be equal."""
        user1 = User(name="Alice", nickname="Ali", age=30)
        user2 = User(name="Alice", nickname="Ali", age=30)
        assert user1 == user2

    def test_equality_with_all_none(self):
        """Users with all None Optional fields should be equal."""
        user1 = User(name="Bob")
        user2 = User(name="Bob")
        assert user1 == user2

    def test_inequality_with_different_values(self):
        """Users with different values should not be equal."""
        user1 = User(name="Alice", age=30)
        user2 = User(name="Alice", age=25)
        assert user1 != user2
