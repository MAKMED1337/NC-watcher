import os
from sqlalchemy.orm import declarative_base
import sqlalchemy
import databases
from sqlalchemy.sql import ClauseElement
from sqlalchemy.engine import URL
from databases.interfaces import Record
from typing import Any

connection_url = URL.create(
	'mysql',
	os.getenv('db_username'),
	os.getenv('db_password'),
	os.getenv('host', 'localhost'),
	os.getenv('port', '3306'),
	os.getenv('db_name')
)

Base = declarative_base()
engine = sqlalchemy.create_engine(connection_url)
db = databases.Database(connection_url.set(drivername='mysql+asyncmy', query={'pool_recycle': '3600'}).render_as_string(False))

async def fetch_all_column(query: ClauseElement | str, values: dict = None) -> list[Record]:
	return [r[0] for r in await db.fetch_all(query, values)]

class AttrDict(dict):
	def __init__(self, *args, **kwargs):
		super(AttrDict, self).__init__(*args, **kwargs)
		self.__dict__ = self

def to_mapping(table: Base) -> AttrDict:
	try:
		keys = table.__table__.columns.keys()
	except Exception:
		keys = table._mapping.keys()

	res = AttrDict()
	for i in keys:
		res[i] = getattr(table, i)
	return res

async def start():
	Base.metadata.create_all(engine)
	await db.connect()