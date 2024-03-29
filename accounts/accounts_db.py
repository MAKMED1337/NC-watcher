from helper.db_config import Base, db, fetch_all_column
from sqlalchemy import Column, VARCHAR
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.mysql import insert

class Accounts(Base):
	__tablename__ = 'Accounts'
	account_id = Column(VARCHAR(64), primary_key=True)
	private_key = Column(VARCHAR(96), primary_key=True)

	#returns random key, that connected
	@staticmethod
	async def get_key(account_id: str) -> str:
		return await db.fetch_val(select(Accounts.private_key).where(Accounts.account_id == account_id))

	@staticmethod
	async def get_keys(account_id: str) -> list[str]:
		return await fetch_all_column(select(Accounts.private_key).where(Accounts.account_id == account_id))

	@staticmethod
	async def is_connected(account_id: str) -> bool:
		return (await db.fetch_one(select(Accounts).where(Accounts.account_id == account_id))) is not None

	@staticmethod
	async def add_account(account_id: str, key: str):
		await db.execute(insert(Accounts).values((account_id, key)).on_duplicate_key_update(private_key=key))

	@staticmethod
	async def delete_key(account_id: str, key: str):
		await db.execute(delete(Accounts).where(and_(Accounts.account_id == account_id, Accounts.private_key == key)))

	# returns list of (account_id, private_key)
	@staticmethod
	async def get_accounts_credentials() -> list[tuple[str, str]]:
		res = {}
		for account_id, key in await db.fetch_all(select(Accounts)): #removing duplicate accounts
			res[account_id] = key
		return list(res.items())