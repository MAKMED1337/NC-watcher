from sqlalchemy import BOOLEAN, INTEGER, VARCHAR, Column, select
from sqlalchemy.dialects.mysql import insert

from helper.db_config import Base, db, to_mapping


class LastTaskState(Base):
    __tablename__ = 'LastTaskState'
    account_id = Column(VARCHAR(64), primary_key=True)
    task_id = Column(INTEGER, primary_key=True)
    ended = Column(BOOLEAN, nullable=False, default=False, server_default='0')
    resubmits = Column(INTEGER)

    @staticmethod
    async def update(account_id: str, task_id: int, ended: bool, resubmits: int | None = None) -> None:
        await db.execute(insert(LastTaskState).values((account_id, task_id, ended, resubmits))
            .on_duplicate_key_update(ended=ended, resubmits=resubmits))

    @staticmethod
    async def bulk_update(values: list['LastTaskState']) -> None:
        stmt = 'INSERT INTO LastTaskState VALUES(:account_id, :task_id, :ended, :resubmits) \
            ON DUPLICATE KEY UPDATE ended = :ended, resubmits = :resubmits' #unable to use ORM for execute many
        await db.execute_many(stmt, [to_mapping(i) for i in values])

    @staticmethod
    async def get(account_id: str) -> list['LastTaskState']:
        return await db.fetch_all(select(LastTaskState).where(LastTaskState.account_id == account_id))
