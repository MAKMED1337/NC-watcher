import os
from sqlalchemy.orm import declarative_base
import sqlalchemy
import databases
from sqlalchemy.sql import ClauseElement
from sqlalchemy.engine import URL
from databases.interfaces import Record

connection_url = URL.create(
	'mysql',
	os.getenv('db_username'),
	os.getenv('db_password'),
	os.getenv('host', 'localhost'),
	os.getenv('port', '3306'),
	'mirror' #db_name
)

Base = declarative_base()
engine = sqlalchemy.create_engine(connection_url)
db = databases.Database(connection_url.set(drivername='mysql+asyncmy', query={'pool_recycle': '3600'}).render_as_string(False))

async def fetch_all_column(query: ClauseElement | str, values: dict = None) -> list[Record]:
	return [r[0] for r in await db.fetch_all(query, values)]

def to_dict(table: Base) -> dict:
	res = table.__dict__
	res.pop('_sa_instance_state')
	return res

async def start():
	Base.metadata.create_all(engine)
	await db.connect()