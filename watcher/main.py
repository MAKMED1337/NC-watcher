from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter, report
from .config import provider, bot

import asyncio
from .paymens_resolver import resolve_payments
from near.providers import FinalityTypes, JsonProviderError
from .last_block import *
from .unpaid_rewards import UnpaidRewards, ActionEnum
import base64
import json
from bot.connected_accounts import ConnectedAccounts
from typing import Any
from helper.db_config import db, start as db_start, to_mapping
from accounts.client import AccountsClient
from.last_task_state import LastTaskState
import aiohttp
from .action_getter import get_updates_for_action
from helper.async_helper import *
from .actions import get_proto_by_enum

coef = None
TRIES = 100
block_logger = None

async def auto_retry(func, *args, **kwargs) -> Any:
	for r in range(TRIES):
		try:
			return await func(*args, **kwargs)
		except Exception:
			if r == TRIES - 1:
				raise
			await asyncio.sleep(1)

async def get_block_by_id(id: int) -> dict | None:
	for i in range(TRIES):
		try:
			return await provider.get_block(id)
		except JsonProviderError as e:
			e = e.args[0]
			if e['cause']['name'] != 'UNKNOWN_BLOCK':
				raise
			return None
		except (aiohttp.ClientResponseError, aiohttp.ClientOSError):
			pass
		
		await asyncio.sleep(1)
	
	print('smth wrong with block', id)

#unordered
async def process_new_blocks(last_processed_block: int, func):
	block = await auto_retry(provider.get_block, finality=FinalityTypes.FINAL)

	if block is None:
		return

	last_block = block['header']['height']
	if last_processed_block is None:
		last_processed_block = last_block - 1
	elif last_processed_block == last_block:
		return

	async def load_and_process(block_id: int):
		block = await get_block_by_id(block_id)
		if block is None:
			return
		await func(block)

	processing_last = asyncio.create_task(func(block))
	for i in range(last_processed_block + 1, last_block, COROS_LIMIT): #to reduce memory usage
		await wait_pool([load_and_process(id) for id in range(i, min(i + COROS_LIMIT, last_block))])
	await processing_last

async def last_block_logger():
	prev = None
	while True:
		block_id = get_last_block_id()
		print('block_id:', block_id)
		if block_id == prev:
			await report(f'blocks stuck on {block_id}')
			break

		prev = block_id
		await asyncio.sleep(5 * 60)

async def add_reward_if_connected(tx_id: str, account_id: str, cost: float, action: ActionEnum, adjustment: int = None):
	if await ConnectedAccounts.is_connected(account_id):
		await UnpaidRewards.add(tx_id, account_id, cost, coef, action, adjustment)

async def process_reward(tx_id: str, args: dict):
	await add_reward_if_connected(tx_id, args['performed_by'], args['mnear_per_task'] * args['verdict'], ActionEnum.task, args['verdict'])
	
	for reviewer, adjustment in zip(args['reviewers'], args['adjustments']):
		if adjustment == 5:
			continue
		assert 0 <= adjustment <= 2
		await add_reward_if_connected(tx_id, reviewer, args['mnear_per_review'], ActionEnum.review, adjustment)

#returns list[hash, args]
def parse_chunk(chunk: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
	result = []
	for transaction in chunk['transactions']:
		if transaction['signer_id'] == 'app.nearcrowd.near':
			for action in transaction['actions']:
				assert 'FunctionCall' in action
				assert len(action) == 1
				f = action['FunctionCall']

				if f['method_name'] != 'starfish_reward4':
					continue
				
				args = json.loads(base64.b64decode(f['args']).decode())
				result.append((transaction['hash'], args))
	return result

#blocks count, chunks count
async def process_blocks() -> tuple[int, int]:
	last_block_id = None
	updates = []
	
	async def process_block(block: dict[str, Any]):
		nonlocal last_block_id, updates

		#block processing
		block_id = block['header']['height']
		if last_block_id is None or block_id > last_block_id:
			last_block_id = block_id
		
		#chunk processing
		#not using semaphore cause already called with semaphore and cause loop(like mutex)
		chunks = await wait_pool([auto_retry(provider.get_chunk, chunk['chunk_hash']) for chunk in block['chunks']], use_semaphore=False)
		for chunk in chunks:
			updates.extend(parse_chunk(chunk))

	await process_new_blocks(get_last_block_id(), process_block)
	async with db.transaction():
		await wait_pool([process_reward(hash, args) for hash, args in updates])
	
		if last_block_id is not None:
			update_last_block_id(last_block_id)

async def resolve_and_pay(account_id: str, action_type: ActionEnum):
	rewards = await UnpaidRewards.get(account_id, action_type)
	actions, states = await get_updates_for_action(account_id, get_proto_by_enum(action_type))
	result = resolve_payments(actions, rewards)
	
	async with db.transaction():
		for action, reward in result:
			await UnpaidRewards.remove_by_tx(reward.tx_id, account_id)
		await LastTaskState.bulk_update([LastTaskState(**to_mapping(i)) for i in states])

		for action, reward in result:
			await bot.notify_payment(action, to_mapping(reward))

async def main():
	global coef, block_logger
	await db_start()
	await bot.connect()
	block_logger = asyncio.create_task(last_block_logger())

	while True:
		async with AccountsClient([]) as c:
			coef = await c.get_coef()
		
		actions = await UnpaidRewards.get_unpaid_action_types()
		tasks = [asyncio.sleep(1)]
		for action in actions:
			tasks.append(resolve_and_pay(action.account_id, action.action))
		await wait_pool(tasks)

		await process_blocks()

async def stop():
	await provider.close()
	await stop_reporter()
	if block_logger is not None:
		block_logger.cancel()

if __name__ == '__main__':
	main_handler(main, report_exception, provider.close)