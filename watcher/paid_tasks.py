from helper.db_config import Base, db, fetch_all_column
from sqlalchemy import Column, VARCHAR, INTEGER
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.mysql import insert

class PaidTasks(Base):
	__tablename__ = 'PaidTasks'
	account_id = Column(VARCHAR(64), primary_key=True)
	task_id = Column(INTEGER, primary_key=True)

	@staticmethod
	async def add(account_id: str, task_id: int):
		await db.execute(insert(PaidTasks).values((account_id, task_id)).on_duplicate_key_update(task_id=task_id)) #INSERT OR INGORE but without warnings

	@staticmethod
	async def get(account_id: str) -> list['PaidTasks']:
		return await fetch_all_column(select(PaidTasks.task_id).where(PaidTasks.account_id == account_id))

	@staticmethod
	async def remove(account_id: str, task_id: int):
		await db.execute(delete(PaidTasks).where(and_(PaidTasks.account_id == account_id, PaidTasks.task_id == task_id)))