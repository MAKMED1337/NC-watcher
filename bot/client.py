PORT = 2002



from helper.IPC import FuncClient
from watcher.actions import IAction
from watcher.unpaid_rewards import UnpaidRewards
from typing import Any

class BotClient(FuncClient):
	def __init__(self):
		super().__init__(PORT)

	async def notify_payment(self, action: IAction, reward: UnpaidRewards, on_exception: Any=Exception):
		return await self.call(on_exception, 'notify_payment', action, reward)

	async def delete_and_notify(self, account_id: str, on_exception: Any=Exception):
		return await self.call(on_exception, 'delete_and_notify', account_id)