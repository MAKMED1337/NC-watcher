from sqlalchemy import BigInteger, Column, insert, select

from helper.db_config import Base, db


class AcknowledgedMessages(Base):
    __tablename__ = 'AcknowledgedMessages'
    id = Column(BigInteger, primary_key=True)

    @staticmethod
    async def is_acknowledged(msg_id: int) -> bool:
        return (await db.fetch_one(select(AcknowledgedMessages).where(AcknowledgedMessages.id == msg_id))) is not None

    @staticmethod
    async def acknowledge(msg_id: int) -> list[str]:
        return await db.execute(insert(AcknowledgedMessages).values((msg_id,)))
