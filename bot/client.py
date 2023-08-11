from typing import Any

from helper.IPC import FuncClient
from watcher.actions import IAction
from watcher.unpaid_rewards import UnpaidRewards

from .config import PORT


class BotClient(FuncClient):
    def __init__(self) -> None:
        super().__init__(PORT)

    async def notify_payment(self, action: IAction, reward: UnpaidRewards, on_exception: Any=Exception) -> None:
        return await self.call(on_exception, 'notify_payment', action, reward)

    async def remove_key(self, account_id: str, private_key: str, on_exception: Any=Exception) -> None:
        return await self.call(on_exception, 'remove_key', account_id, private_key)

    async def notify_mod_message(self, account_id: str, msg: str, on_exception: Any=Exception) -> None:
        return await self.call(on_exception, 'notify_mod_message', account_id, msg)
