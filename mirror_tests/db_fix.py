import helper.db_config as config
from sqlalchemy.engine import URL
import sqlalchemy
import databases
import os

config.connection_url = URL.create(
	'mysql',
	os.getenv('db_username'),
	os.getenv('db_password'),
	os.getenv('host', 'localhost'),
	os.getenv('port', '3306'),
	'mirror_test'
)

config.engine = sqlalchemy.create_engine(config.connection_url)
config.db = databases.Database(config.connection_url.set(drivername='mysql+asyncmy', query={'pool_recycle': '3600'}).render_as_string(False))
