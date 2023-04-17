from helper.db_config import Base, db, fetch_all_column
from sqlalchemy import Column, VARCHAR, BigInteger
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.mysql import insert

class ConnectedAccounts(Base):
	__tablename__ = 'ConnectedAccounts'
	tg_id = Column(BigInteger, primary_key=True)
	account_id = Column(VARCHAR(64), primary_key=True)

	@staticmethod
	async def is_connected(account_id: str) -> bool:
		return (await db.fetch_one(select(ConnectedAccounts).where(ConnectedAccounts.account_id == account_id))) is not None
	
	@staticmethod
	async def get_watched_accounts() -> list[str]:
		return await fetch_all_column(select(ConnectedAccounts.account_id).distinct())

	@staticmethod
	async def add(tg_id: int, account_id: str):
		await db.execute(insert(ConnectedAccounts).values((tg_id, account_id)).on_duplicate_key_update())

	@staticmethod
	async def remove(tg_id: int, account_id: str):
		await db.execute(delete(ConnectedAccounts).where(and_(ConnectedAccounts.tg_id == tg_id, ConnectedAccounts.account_id == account_id)))