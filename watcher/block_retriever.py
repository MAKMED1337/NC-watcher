import asyncio
from helper.provider_config import provider
from near.providers import FinalityTypes, JsonProviderError
from .last_block import *
from typing import Any
from helper.async_helper import *

TRIES = 100

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
		except Exception:
			pass
		
		await asyncio.sleep(1)
	
	print('smth wrong with block', id)

#unordered
async def retrieve_new_blocks(last_processed_block: int, func):
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