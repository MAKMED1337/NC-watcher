import os
from typing import Any

import databases
import sqlalchemy
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base

connection_url = URL.create(
    'mysql',
    os.getenv('DB_USERNAME'),
    os.getenv('DB_PASSWORD'),
    os.getenv('HOST', 'localhost'),
    os.getenv('PORT', '3306'),
    os.getenv('DB_NAME'),
)

Base = declarative_base()
engine = sqlalchemy.create_engine(connection_url)
db = databases.Database(connection_url.set(drivername='mysql+asyncmy', query={'pool_recycle': '3600'}).render_as_string(False))

class AttrDict(dict):
    def __init__(self, *args: list[Any], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.__dict__ = self

def to_mapping(table: Base) -> AttrDict:
    try:
        keys = table.__table__.columns.keys()
    except AttributeError:
        keys = table._mapping.keys()  # noqa: SLF001

    res = AttrDict()
    for i in keys:
        res[i] = getattr(table, i)
    return res

async def start() -> None:
    Base.metadata.create_all(engine)
    await db.connect()
