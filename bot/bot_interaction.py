from helper.bot_config import bot, command_to_regex
import asyncio
from telethon import events
import json
from helper.db_config import db
from accounts.client import AccountsClient, SingleAccountsClient
from watcher.actions import IAction, load_action_by_info, modes
from watcher.last_task_state import LastTaskState
from watcher.unpaid_rewards import UnpaidRewards
from .connected_accounts import ConnectedAccounts
import html
from enum import Enum

def get_account_id(s: str) -> str | None:
	start = 'near-api-js:keystore:'
	ending = ':mainnet'

	if s.startswith(start) and s.endswith(ending):
		return s[len(start):-len(ending)]

#only adds account, doesn't connect
async def add_account_unsafe(account_id: str, private_key: str):
	async with db.transaction():
		async with AccountsClient([]) as c:
			if not await c.add_key(account_id, private_key):
				return False
		
		already_connected = await ConnectedAccounts.is_connected(account_id)
		print(account_id, '->', 'connected' if already_connected else 'new')
		if already_connected:
			return True
		
		#adding data into db
		async with SingleAccountsClient(account_id) as c:
			assert c.connected
			
			mode_tasks = await asyncio.gather(*[c.get_task_list(mode) for mode in modes.keys()])
			state = await LastTaskState.get(account_id)
			ended_tasks = set([i.task_id for i in state if i.ended])

			actions = []
			for tasks in mode_tasks:
				if tasks is None:
					continue
				
				for i in tasks:
					if i.task_id in ended_tasks:
						continue
					
					actions.append(load_action_by_info(c, i))

			actions: list[IAction] = await asyncio.gather(*actions)

			await LastTaskState.bulk_update([LastTaskState(account_id=account_id, task_id=i.task_id, ended=i.has_ended(), resubmits=i.info.resubmits) for i in actions])
			await UnpaidRewards.clear(account_id)
	return True

class AdditionStatus(Enum):
	ok = 0
	bad = 1
	bug = 2

async def add_account(account_id: str, private_key: str) -> AdditionStatus:
	try:
		if await add_account_unsafe(account_id, private_key):
			return AdditionStatus.ok
		else:
			return AdditionStatus.bad
	except Exception:
		return AdditionStatus.bug

@bot.on(events.NewMessage(pattern=command_to_regex('list')))
async def get_accounts_list(msg):
	accounts = await ConnectedAccounts.get_connected_accounts(msg.sender_id)
	text = ''
	for account_id in accounts:
		text += f'<code>{account_id}</code>\n'
	await msg.reply(text)
	raise events.StopPropagation

@bot.on(events.NewMessage(incoming=True))
async def add_accounts_handler(msg):
	try:
		accounts = json.loads(html.unescape(msg.text))
	except Exception:
		return await msg.reply('Invalid JSON')

	data = []
	for k, v in accounts.items():
		account_id = get_account_id(k)
		if account_id is None:
			continue
		data.append((account_id, v))
	statuses = await asyncio.gather(*[add_account(*i) for i in data])
	
	ok, bad, bug = [], [], []
	for (account_id, private_key), status in zip(data, statuses):
		if status == AdditionStatus.ok:
			await ConnectedAccounts.add(msg.sender_id, account_id, private_key)
			ok.append(account_id)
		elif status == AdditionStatus.bad:
			bad.append(account_id)
		else:
			bug.append(account_id)

	text = 'Succesfully connected:\n'
	for account_id in ok:
		text += f'<code>{account_id}</code>\n'

	if len(bad) > 0:
		text += '\nWasn\'t connected:\n'
		for account_id in bad:
			text += f'<code>{account_id}</code>\n'

	if len(bug) > 0:
		text += '\nBugged(report to admins):\n'
		for account_id in bug:
			text += f'<code>{account_id}</code>\n'
	
	await msg.reply(text[:4096])