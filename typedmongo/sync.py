"""
Synchronize the asyncio module to the root module.
"""

import pathlib


def main(just_check: bool = False):
    exit_code = 0
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
            .replace(
                "from motor.motor_asyncio import AsyncIOMotorClientSession as MongoSession",
                "from pymongo.client_session import ClientSession as MongoSession",
            )
            .replace("async def ", "def ")
            .replace("await ", "")
            .replace("async for ", "for ")
            .replace("async with ", "with ")
            .replace("AsyncIterable", "Iterable")
            .replace(
                "AsyncGenerator[MongoSession, None]",
                "Generator[MongoSession, None, None]",
            )
            .replace("AsyncGenerator[None, None]", "Generator[None, None, None]")
            .replace("AsyncGenerator", "Generator")
            .replace("asynccontextmanager", "contextmanager")
        )
        if just_check:
            if content != new_file_path.read_text():
                print(f"File {new_file_path} is not synchronized.")
                exit_code = 1
        else:
            new_file_path.write_text(content)
    return exit_code


if __name__ == "__main__":
    import sys

    sys.exit(main("--check" in " ".join(sys.argv[1:])))
