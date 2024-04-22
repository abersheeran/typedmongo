"""
Synchronize the asyncio module to the root module.
"""
import pathlib


def main():
    sync_dir = pathlib.Path(__file__).absolute().parent
    asyncio_dir = pathlib.Path(__file__).absolute().parent / "asyncio"
    for path in asyncio_dir.glob("*.py"):
        new_file_path = sync_dir / path.name
        content = path.read_text()
        content = (
            content.replace(
                "from motor.motor_asyncio import AsyncIOMotorCollection",
                "from pymongo.collection import Collection",
            )
            .replace(
                "from motor.motor_asyncio import AsyncIOMotorDatabase",
                "from pymongo.database import Database",
            )
            .replace("async def ", "def ")
            .replace("await ", "")
            .replace("async for ", "for ")
            .replace("async with ", "with ")
            .replace("AsyncIterable", "Iterable")
        )
        new_file_path.write_text(content)


if __name__ == "__main__":
    main()
