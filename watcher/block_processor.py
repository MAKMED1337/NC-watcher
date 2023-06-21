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
from .processed_blocks import ProcessedBlocks

coef = None

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

async def verify_keys(account_id: str):
	if await ConnectedAccounts.is_connected(account_id):
		async with AccountsClient([]) as c:
			await c.verify_keys(account_id)

#returns list[hash, args]
async def process_chunk(chunk: dict[str, Any]):
	for transaction in chunk['transactions']:
		if transaction['signer_id'] == 'app.nearcrowd.near':
			for action in transaction['actions']:
				assert 'FunctionCall' in action
				assert len(action) == 1
				f = action['FunctionCall']

				if f['method_name'] != 'starfish_reward4':
					continue
				
				args = json.loads(base64.b64decode(f['args']).decode())
				await process_reward(transaction['hash'], args)
		
		for action in transaction['actions']:
			if 'DeleteKey' in action:
				await verify_keys(transaction['signer_id'])

#blocks count, chunks count
async def process_new_blocks() -> tuple[int, int]:
	async def process_block(block: dict[str, Any]):
		block_id = block['header']['height']
		
		#chunk processing
		#not using semaphore cause already called with semaphore and cause loop(like mutex)
		chunks = await wait_pool([auto_retry(provider.get_chunk, chunk['chunk_hash']) for chunk in block['chunks']], use_semaphore=False)

		async with db.transaction():
			for chunk in chunks:
				await process_chunk(chunk)
			await ProcessedBlocks.set_processed(block_id)

	await retrieve_new_blocks(process_block)

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