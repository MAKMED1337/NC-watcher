PORT = 2002



from helper.IPC import Client
from watcher.actions import IAction
from watcher.unpaid_rewards import UnpaidRewards

class BotClient(Client):
	def __init__(self):
		super().__init__(PORT)

	async def add_payment(self, action: IAction, reward: UnpaidRewards):
		await self.send((action, reward))