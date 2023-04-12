from helper.main_handler import main_handler
from helper.report_exceptions import report_exception
from .config import provider

import asyncio
from .paymens_resolver import resolve_payments
from .actions import get_proto_by_enum
from near.providers import FinalityTypes, JsonProviderError
from .last_block import *
from payments.client import PaymentsClient
from .unpaid_rewards import UnpaidRewards, ActionEnum
from .paid_tasks import PaidTasks
import base64
import json
import traceback
from .watcher_accounts import WatcherAccounts
from typing import Any
from helper.db_config import start as db_start
from accounts.client import AccountsClient
import aiohttp

coef = None
payments = PaymentsClient()

async def auto_retry(func, *args, **kwargs) -> Any:
	retries = 100
	for r in range(retries):
		try:
			return await func(*args, **kwargs)
		except BaseException:
			if r == retries - 1:
				raise

async def get_block_by_id(id: int) -> dict:
	for i in range(100):
		try:
			return await provider.get_block(id)
		except JsonProviderError as e:
			e = e.args[0]
			if e['cause']['name'] != 'UNKNOWN_BLOCK':
				print(e)
			return None
		except (aiohttp.ClientResponseError, aiohttp.ClientOSError):
			pass
		except BaseException as e:
			traceback.print_exception(e)
		await asyncio.sleep(1)
	
	print('smth wrong with block', id)

async def get_new_blocks(last_block_id: int) -> list[dict]:
	block = await auto_retry(provider.get_block, finality=FinalityTypes.FINAL)
	if block is None:
		return []

	if last_block_id is None:
		last_block_id = block['header']['height'] - 1
	elif last_block_id == block['header']['height']:
		return []
	
	result = await asyncio.gather(*[get_block_by_id(id) for id in range(last_block_id + 1, block['header']['height'])])
	result.append(block)

	return list(filter(None, result))

async def add_reward_if_connected(tx_id: str, account_id: str, cost: float, action: ActionEnum, adjustment: int = None):
	if await WatcherAccounts.is_connected(account_id):
		await UnpaidRewards.add(tx_id, account_id, cost, coef, action, adjustment)

async def process_reward(tx_id: str, args: dict):
	await add_reward_if_connected(tx_id, args['performed_by'], args['mnear_per_task'] * args['verdict'], ActionEnum.task, args['verdict'])
	
	for reviewer, adjustment in zip(args['reviewers'], args['adjustments']):
		if adjustment == 5:
			continue
		assert 0 <= adjustment <= 2
		await add_reward_if_connected(tx_id, reviewer, args['mnear_per_review'], ActionEnum.review, adjustment)

async def process_blocks() -> int:
	blocks = await get_new_blocks(get_last_block_id())

	if len(blocks) == 0:
		return 0
	set_last_block_id(blocks[-1]['header']['height'])

	chunks = []
	for block in blocks:
		chunks.extend([auto_retry(provider.get_chunk, chunk['chunk_hash']) for chunk in block['chunks']])
	chunks = await asyncio.gather(*chunks)
	
	process_reward_tasks = []
	for chunk in chunks:
		for transaction in chunk['transactions']:
			if transaction['signer_id'] == 'app.nearcrowd.near':
				for action in transaction['actions']:
					assert 'FunctionCall' in action
					assert len(action) == 1
					f = action['FunctionCall']

					if f['method_name'] != 'starfish_reward4':
						continue
					
					args = json.loads(base64.b64decode(f['args']).decode())
					process_reward_tasks.append(process_reward(transaction['hash'], args))
	await asyncio.gather(*process_reward_tasks)
	return len(blocks)

async def resolve_and_pay(account_id: str, action: ActionEnum):
	result = await resolve_payments(account_id, get_proto_by_enum(action))
	
	if result is None:
		return
	
	await UnpaidRewards.remove(account_id, action)
	for action, reward in result:
		await payments.add_payment(action, reward)
		await PaidTasks.add(account_id, action.info.task_id)

async def main():
	global coef
	await db_start()
	await payments.connect()

	while True:
		async with AccountsClient([]) as c:
			coef = await c.get_coef()
		
		await process_blocks()
		
		entities = await UnpaidRewards.get_unpaid_actions()
		tasks = [asyncio.sleep(1)]
		for entity in entities:
			tasks.append(resolve_and_pay(entity.account_id, entity.action))
		await asyncio.gather(*tasks)

async def stop():
	await provider.close()

if __name__ == '__main__':
	main_handler(main, report_exception, provider.close)