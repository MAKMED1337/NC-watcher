import asyncio
from accounts.client import AccountsClient, SingleAccountsClient
from .last_task_state import LastTaskState
from bot.connected_accounts import ConnectedAccounts
from helper.db_config import start as db_start, db
from .actions import modes
import json
from .unpaid_rewards import UnpaidRewards
from .actions import *
import traceback

def get_account_id(s: str) -> str | None:
	start = 'near-api-js:keystore:'
	ending = ':mainnet'

	if s.startswith(start) and s.endswith(ending):
		return s[len(start):-len(ending)]

async def safe_load_action(account: SingleAccountsClient, task: ListTaskInfo) -> IAction:
	try:
		return await load_action_by_info(account, task)
	except Exception:
		print(account.account_id, task, traceback.format_exc())

async def add_account(account_id: str, private_key: str):
	async with db.transaction():
		async with AccountsClient([]) as c:
			await c.add_key(account_id, private_key)
		
		async with SingleAccountsClient(account_id) as c:
			if not c.connected:
				print(f'cannot connect to {account_id}')
				return
			
			mode_tasks = await asyncio.gather(*[c.get_task_list(mode) for mode in modes.keys()])
			state = await LastTaskState.get(account_id)
			ended_tasks = set([i.task_id for i in state if i.ended])

			actions = []
			for tasks in mode_tasks:
				if tasks is None:
					print('WTF:', account_id)
					continue
				
				for i in tasks:
					if i.task_id in ended_tasks:
						continue
					
					actions.append(safe_load_action(c, i))

			actions: list[IAction] = await asyncio.gather(*actions)

		
			await LastTaskState.bulk_update([LastTaskState(account_id=account_id, task_id=i.task_id, ended=i.has_ended(), resubmits=i.info.resubmits) for i in actions])
			await UnpaidRewards.clear(account_id)
	print('OK:', account_id)

async def main():
	await db_start()
	data = []
	for k, v in json.load(open('sessionStorage.json', 'r')).items():
		account_id = get_account_id(k)
		if account_id is None:
			continue
		data.append((account_id, v))
	await asyncio.gather(*[add_account(*i) for i in data])
asyncio.run(main())