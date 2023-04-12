from .actions import IAction, modes
from accounts.client import SingleAccountsClient
from .paid_tasks import PaidTasks
import asyncio
from reporter.client import ReporterClient

async def get_unpaid_tasks_for_mode(account: SingleAccountsClient, mode: int, paid: set, action: IAction) -> list[IAction]:
	tasks = [r for r in await account.get_task_list(mode) if r.task_id not in paid]
	
	actions = []
	for info in tasks:
		if not action.is_proto(info):
			continue
		
		actions.append(action.load(account, info))
	
	actions = await asyncio.gather(*actions)
	return [i for i in actions if i.has_ended()]

async def get_unpaid_actions(account_id: str, action: IAction) -> list[IAction]:
	async with SingleAccountsClient(account_id) as account:
		if not account.connected:
			async with ReporterClient() as r:
				await r.report(f'no such account: {account_id}')
			return {}

		paid = set(await PaidTasks.get(account_id))

		unpaid = []
		for r in await asyncio.gather(*[get_unpaid_tasks_for_mode(account, mode, paid, action) for mode in modes]):
			unpaid.extend(r)
		return unpaid