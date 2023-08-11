import enum

from sqlalchemy import FLOAT, INTEGER, VARCHAR, Column, Enum, and_, delete, select
from sqlalchemy.dialects.mysql import insert

from helper.db_config import Base, db


class ActionEnum(enum.Enum):
    task = 0
    review = 1

class UnpaidRewards(Base):
    __tablename__ = 'UnpaidRewards'
    tx_id = Column(VARCHAR(64), primary_key=True)
    account_id = Column(VARCHAR(64), primary_key=True)
    cost = Column(INTEGER, nullable=False)
    coef = Column(FLOAT, nullable=False)
    action = Column(Enum(ActionEnum), nullable=False)
    adjustment = Column(INTEGER) #OR verdict for task

    @staticmethod
    async def add(tx_id: str, account_id: str, cost: int, coef: float, action: ActionEnum, adjustment: int | None = None) -> None:
        print('new reward:', tx_id, account_id, cost, coef, action, adjustment)
        await db.execute(insert(UnpaidRewards).values((tx_id, account_id, cost, coef, action, adjustment)).on_duplicate_key_update(tx_id=tx_id))

    @staticmethod
    async def get(account_id: str, action: ActionEnum) -> list['UnpaidRewards']:
        return await db.fetch_all(select(UnpaidRewards).where(and_(UnpaidRewards.account_id == account_id, UnpaidRewards.action == action)))

    @staticmethod
    async def remove(account_id: str, action: ActionEnum) -> None:
        await db.execute(delete(UnpaidRewards).where(and_(UnpaidRewards.account_id == account_id, UnpaidRewards.action == action)))

    @staticmethod
    async def remove_by_tx(tx_id: str, account_id: str) -> None:
        await db.execute(delete(UnpaidRewards).where(and_(UnpaidRewards.tx_id == tx_id, UnpaidRewards.account_id == account_id)))

    @staticmethod
    async def clear(account_id: str) -> None:
        await db.execute(delete(UnpaidRewards).where(and_(UnpaidRewards.account_id == account_id)))

    @staticmethod
    async def get_unpaid_action_types() -> list[tuple[str, ActionEnum]]:
        return await db.fetch_all(select(UnpaidRewards.account_id, UnpaidRewards.action).distinct())
