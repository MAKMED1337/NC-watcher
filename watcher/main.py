from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter, report
from .config import provider, bot

import asyncio
from .paymens_resolver import resolve_payments
from .unpaid_rewards import UnpaidRewards, ActionEnum
from typing import Any
from helper.db_config import db, start as db_start, to_mapping
from accounts.client import AccountsClient
from.last_task_state import LastTaskState
from .action_getter import get_updates_for_action
from helper.async_helper import *
from .actions import get_proto_by_enum
from .block_processor import process_new_blocks, coef, last_block_logger #import coef, cause circular import

block_logger = None

async def resolve_and_pay(account_id: str, action_type: ActionEnum):
	async with db.transaction():
		actions, states = await get_updates_for_action(account_id, get_proto_by_enum(action_type))
		rewards = await UnpaidRewards.get(account_id, action_type)
		result = resolve_payments(actions, rewards)
	
		for action, reward in result:
			await UnpaidRewards.remove_by_tx(reward.tx_id, account_id)
		await LastTaskState.bulk_update([LastTaskState(**to_mapping(i)) for i in states])

		for action, reward in result:
			await bot.notify_payment(action, to_mapping(reward))

async def fetch_coef():
	global coef
	while True:
		async with AccountsClient([]) as c:
			coef = await c.get_coef(None)
			if coef is not None:
				return
		await asyncio.sleep(1)

async def main():
	global coef, block_logger
	await db_start()
	await bot.connect()
	block_logger = asyncio.create_task(last_block_logger())

	while True:
		await fetch_coef()
		
		actions = await UnpaidRewards.get_unpaid_action_types()
		tasks = [asyncio.sleep(1)]
		for account_id, action in actions:
			tasks.append(resolve_and_pay(account_id, action))
		await wait_pool(tasks)

		await process_new_blocks()

async def stop():
	await provider.close()
	await stop_reporter()
	if block_logger is not None:
		block_logger.cancel()

if __name__ == '__main__':
	main_handler(main, report_exception, stop)