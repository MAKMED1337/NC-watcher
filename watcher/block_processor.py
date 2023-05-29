import asyncio
from helper.report_exceptions import report
from helper.provider_config import provider
from .block_retriever import retrieve_new_blocks, auto_retry
from .last_block import *
from .unpaid_rewards import UnpaidRewards, ActionEnum
import base64
import json
from bot.connected_accounts import ConnectedAccounts
from typing import Any
from helper.db_config import db
from accounts.client import AccountsClient
from helper.async_helper import *
from .config import block_logger_interval

coef = None
removed_keys = []

def set_coef(c: float):
	global coef
	coef = c

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

async def verify_keys(c: AccountsClient, account_id: str):
	if await ConnectedAccounts.is_connected(account_id):
		await c.verify_keys(account_id)

#returns list[hash, args]
def parse_chunk(chunk: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
	global removed_keys

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
		
		for action in transaction['actions']:
			if 'DeleteKey' in action:
				removed_keys.append(transaction['signer_id'])
	
	return result

#blocks count, chunks count
async def process_new_blocks() -> tuple[int, int]:
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

	await retrieve_new_blocks(get_last_block_id(), process_block)

	async with AccountsClient([]) as c:
		global removed_keys
		await wait_pool([verify_keys(c, account_id) for account_id in removed_keys])
		removed_keys.clear()

	async with db.transaction():
		await wait_pool([process_reward(hash, args) for hash, args in updates])

		if last_block_id is not None:
			update_last_block_id(last_block_id)

async def last_block_logger():
	prev = None
	while True:
		block_id = get_last_block_id()
		print('block_id:', block_id)
		if block_id == prev:
			await report(f'blocks stuck on {block_id}')
			exit(1)

		prev = block_id
		await asyncio.sleep(block_logger_interval.seconds)