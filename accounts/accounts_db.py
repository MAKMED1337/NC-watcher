from helper.db_config import Base, db
from sqlalchemy import Column, VARCHAR
from sqlalchemy import select, insert, delete

class Accounts(Base):
	__tablename__ = 'Accounts'
	account_id = Column(VARCHAR(64), primary_key=True)
	private_key = Column(VARCHAR(96), nullable=False)

	@staticmethod
	async def get_key(account_id: str) -> str:
		return await db.fetch_val(select(Accounts.private_key).where(Accounts.account_id == account_id))

	@staticmethod
	async def is_connected(account_id: str) -> bool:
		return (await db.fetch_one(select(Accounts).where(Accounts.account_id == account_id))) is not None

	@staticmethod
	async def add_account(account_id: str, key: str):
		await db.execute(insert(Accounts).values((account_id, key)))

	@staticmethod
	async def delete_account(account_id: str):
		await db.execute(delete(Accounts).where(Accounts.account_id == account_id))

	# returns list of (account_id, private_key)
	@staticmethod
	async def get_accounts_credentials() -> list:
		return await db.fetch_all(select(Accounts))