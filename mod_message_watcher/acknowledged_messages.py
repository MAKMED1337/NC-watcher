from helper.db_config import Base, db
from sqlalchemy import Column, BigInteger
from sqlalchemy import select, insert

class AcknowledgedMessages(Base):
	__tablename__ = 'ConnectedAccounts'
	id = Column(BigInteger, primary_key=True)	

	@staticmethod
	async def is_acknowledged(msg_id: int) -> bool:
		return (await db.fetch_one(select(AcknowledgedMessages).where(AcknowledgedMessages.id == msg_id))) is not None
	
	@staticmethod
	async def acknowledge(msg_id: int) -> list[str]:
		return await db.execute(insert(AcknowledgedMessages).values((msg_id,)))