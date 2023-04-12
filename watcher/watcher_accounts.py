from helper.db_config import Base, db
from sqlalchemy import Column, VARCHAR
from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

class WatcherAccounts(Base):
	__tablename__ = 'WatcherAccounts'
	account_id = Column(VARCHAR(64), primary_key=True)

	@staticmethod
	async def is_connected(account_id: str) -> bool:
		return (await db.fetch_one(select(WatcherAccounts).where(WatcherAccounts.account_id == account_id))) is not None

	@staticmethod
	async def add(account_id: str):
		await db.execute(insert(WatcherAccounts).values((account_id,)).on_duplicate_key_update(account_id=account_id))

	@staticmethod
	async def remove(account_id: str):
		await db.execute(delete(WatcherAccounts).where(WatcherAccounts.account_id == account_id))