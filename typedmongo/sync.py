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
                "from pymongo.asynchronous.client_session import AsyncClientSession",
                "from pymongo.synchronous.client_session import ClientSession",
            )
            .replace(
                "from pymongo.asynchronous.collection import AsyncCollection",
                "from pymongo.synchronous.collection import Collection",
            )
            .replace(
                "from pymongo.asynchronous.database import AsyncDatabase",
                "from pymongo.synchronous.database import Database",
            )
            .replace("from pymongo.asynchronous", "from pymongo.synchronous")
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
