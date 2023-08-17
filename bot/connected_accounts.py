from typing import Any

from sqlalchemy import VARCHAR, BigInteger, and_, delete, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Mapped, mapped_column

from helper.db_config import Base, db


class ConnectedAccounts(Base):
    __tablename__ = 'ConnectedAccounts'
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[str] = mapped_column(VARCHAR(64), primary_key=True)
    private_key: Mapped[str] = mapped_column(VARCHAR(96))


    @staticmethod
    def _where(tg_id: int, account_id: str, sql: Any) -> Any:
        return sql.where(and_(ConnectedAccounts.tg_id == tg_id, ConnectedAccounts.account_id == account_id))

    @staticmethod
    async def is_connected(account_id: str) -> bool:
        return (await db.fetch_one(select(ConnectedAccounts).where(ConnectedAccounts.account_id == account_id))) is not None

    @staticmethod
    async def get_watched_accounts() -> list[str]:
        return await db.fetch_column(select(ConnectedAccounts.account_id).distinct())

    @staticmethod
    async def add(tg_id: int, account_id: str, private_key: str) -> None:
        await db.execute(insert(ConnectedAccounts).values((tg_id, account_id, private_key)).on_duplicate_key_update(private_key=private_key))

    @staticmethod
    async def disconnect(tg_id: int, account_id: str) -> None:
        await db.execute(ConnectedAccounts._where(tg_id, account_id, delete(ConnectedAccounts)))

    @staticmethod
    async def get_tg(account_id: str) -> list[int]:
        return await db.fetch_column(select(ConnectedAccounts.tg_id).where(ConnectedAccounts.account_id == account_id))

    @staticmethod
    async def get_tg_by_key(account_id: str, private_key: str) -> list[str]:
        return await db.fetch_column(select(ConnectedAccounts.tg_id).where(
            and_(ConnectedAccounts.account_id == account_id, ConnectedAccounts.private_key == private_key)))

    @staticmethod
    async def remove_key(account_id: str, private_key: str) -> None:
        await db.execute(delete(ConnectedAccounts).where(
            and_(ConnectedAccounts.account_id == account_id, ConnectedAccounts.private_key == private_key)))

    @staticmethod
    async def get_connected_accounts(tg_id: int) -> list[str]:
        return await db.fetch_column(select(ConnectedAccounts.account_id).where(ConnectedAccounts.tg_id == tg_id))
