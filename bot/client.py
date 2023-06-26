PORT = 2002



from helper.IPC import FuncClient # noqa: E402
from watcher.actions import IAction # noqa: E402
from watcher.unpaid_rewards import UnpaidRewards # noqa: E402
from typing import Any # noqa: E402

class BotClient(FuncClient):
	def __init__(self):
		super().__init__(PORT)

	async def notify_payment(self, action: IAction, reward: UnpaidRewards, on_exception: Any=Exception):
		return await self.call(on_exception, 'notify_payment', action, reward)

	async def remove_key(self, account_id: str, private_key: str, on_exception: Any=Exception):
		return await self.call(on_exception, 'remove_key', account_id, private_key)

	async def notify_mod_message(self, account_id: str, msg: str, on_exception: Any=Exception):
		return await self.call(on_exception, 'notify_mod_message', account_id, msg)