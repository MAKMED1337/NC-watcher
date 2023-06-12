from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter
from .config import bot, review_watcher_interval

import asyncio
from helper.provider_config import provider
from .paymens_resolver import resolve_payments
from .unpaid_rewards import UnpaidRewards, ActionEnum
from helper.db_config import db, start as db_start, to_mapping
from accounts.client import AccountsClient
from.last_task_state import LastTaskState
from .action_getter import get_updates_for_action
from helper.async_helper import *
from .actions import get_proto_by_enum
from .block_processor import process_new_blocks, set_coef, coef, last_block_logger #import coef, cause circular import
from .actions import *
from bot.connected_accounts import ConnectedAccounts

block_logger = None
wrong_review_watcher = None

def split_tx_dependent(actions: list[IAction]) -> tuple[list[IAction], list[IAction]]:
	f = lambda i: isinstance(i, Task) or i.calculate_cost() != 0
	return [i for i in actions if f(i)], [i for i in actions if not f(i)]

def reward_from_action(account_id: str, action: IAction):
	return UnpaidRewards(tx_id='NULL', account_id=account_id, cost=action.calculate_cost(), coef=coef, action=action.get_enum(), adjustment=1)

async def resolve_and_pay(account_id: str, action_type: ActionEnum):
	async with db.transaction():
		actions, states = await get_updates_for_action(account_id, get_proto_by_enum(action_type))
		tx_actions, free_actions = split_tx_dependent(actions) #some actions don't appear in txs

		rewards = await UnpaidRewards.get(account_id, action_type)
		result = resolve_payments(tx_actions, rewards)
		
		if result is None or len(free_actions) == 0:
			return

		print(account_id, action_type, '->')
		for action, reward in result:
			print(action.info, to_mapping(reward))
		
		for action in free_actions:
			print(action.info, 'NULL')
		
		for state in states:
			print(to_mapping(state))
		print('end')

		for action, reward in result:
			await UnpaidRewards.remove_by_tx(reward.tx_id, account_id)
		await LastTaskState.bulk_update([LastTaskState(**to_mapping(i)) for i in states])

		for action, reward in result:
			await bot.notify_payment(action, to_mapping(reward))
		for action in free_actions:
			await bot.notify_payment(action, reward_from_action(account_id, action))

async def fetch_coef():
	while True:
		async with AccountsClient([]) as c:
			coef = await c.get_coef(None)
			if coef is not None:
				set_coef(coef)
				return
		await asyncio.sleep(1)

async def review_watcher():
	while True:
		tasks = []
		for account_id in await ConnectedAccounts.get_watched_accounts():
			tasks.append(resolve_and_pay(account_id, ActionEnum.review))
		await wait_pool(tasks)
		await asyncio.sleep(review_watcher_interval.seconds)

async def start():
	global block_logger, wrong_review_watcher
	provider.start()
	await db_start()
	await bot.connect()
	block_logger = asyncio.create_task(last_block_logger())
	wrong_review_watcher = asyncio.create_task(review_watcher())

async def iteration():
	await fetch_coef()
	await process_new_blocks()
	
	actions = await UnpaidRewards.get_unpaid_action_types()
	tasks = [asyncio.sleep(1)]
	for account_id, action in actions:
		tasks.append(resolve_and_pay(account_id, action))
	await wait_pool(tasks)

async def main():
	await start()
	while True:
		await iteration()

async def stop():
	await provider.close()
	await stop_reporter()
	if block_logger is not None:
		block_logger.cancel()
	if wrong_review_watcher is not None:
		wrong_review_watcher.cancel()

if __name__ == '__main__':
	main_handler(main, report_exception, stop)