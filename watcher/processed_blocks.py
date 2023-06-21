from helper.db_config import Base, db, fetch_all_column
from sqlalchemy import Column, INTEGER, BOOLEAN
from sqlalchemy import select, update, insert
from sqlalchemy import func

class ProcessedBlocks(Base):
	__tablename__ = 'ProcessedBlocks'
	block_id = Column(INTEGER, primary_key=True)
	processed = Column(BOOLEAN, nullable=False, default=False, server_default='0')

	@staticmethod
	async def get_last_id() -> int | None:
		return await db.fetch_val(select(func.max(ProcessedBlocks.block_id)))

	@staticmethod
	async def set_processed(block_id: int):
		await db.execute(update(ProcessedBlocks).where(ProcessedBlocks.block_id == block_id).values(processed=True))
	
	@staticmethod
	async def get_unprocessed() -> list[int]:
		return await fetch_all_column(select(ProcessedBlocks.block_id).where(ProcessedBlocks.processed == False))

	@staticmethod
	#[start, finish]
	async def add_range(start: int, finish: int):
		await db.execute_many(insert(ProcessedBlocks), [{'block_id': i, 'processed': False} for i in range(start, finish + 1)])