import asyncio
from accounts.client import SingleAccountsClient
from .paid_tasks import PaidTasks
from bot.connected_accounts import ConnectedAccounts
from helper.db_config import start as db_start
from .actions import modes
from pathlib import Path
import json
from .unpaid_rewards import UnpaidRewards
from .actions import *
import traceback

def get_account_id(s: str) -> str | None:
	start = 'near-api-js:keystore:'
	ending = ':mainnet'

	if s.startswith(start) and s.endswith(ending):
		return s[len(start):-len(ending)]

async def add_paid_task_if_ended(account: SingleAccountsClient, task: ListTaskInfo):
	try:
		action = await load_action_by_info(account, task)
		if action.has_ended():
			await PaidTasks.add(account.account_id, task.task_id)
	except BaseException:
		print(account.account_id, task, traceback.format_exc())

async def add_account(account_id: str):
	async with SingleAccountsClient(account_id) as c:
		if not c.connected:
			print(f'cannot connect to {account_id}')
			return
		
		mode_tasks = await asyncio.gather(*[c.get_task_list(mode) for mode in modes.keys()])
		coros = []
		for tasks in mode_tasks:
			for i in tasks:
				coros.append(add_paid_task_if_ended(c, i))

		await asyncio.gather(*coros)
	
	await UnpaidRewards.clear(account_id)
	await ConnectedAccounts.add(793975166, account_id)

async def main():
	await db_start()
	data = []
	for k, v in json.load(open(Path(__file__).parent / 'sessionStorage.json', 'r')).items():
		account_id = get_account_id(k)
		if account_id is None:
			continue
		data.append(account_id)
	await asyncio.gather(*[add_account(i) for i in data])
asyncio.run(main())