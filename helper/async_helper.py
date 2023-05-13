import asyncio
from typing import Any, AsyncGenerator

COROS_LIMIT = 10000
semaphore = asyncio.Semaphore(COROS_LIMIT)

async def sem_coro(coro):
	async with semaphore:
		return await coro

#unordered, unsafe(manual exception handling)
async def generator_pool(coros: list) -> AsyncGenerator[Any, None]:
	for i in asyncio.as_completed([sem_coro(c) for c in coros]):
		yield await i

#TODO proper exception handling
async def wait_pool(coros: list, *, use_semaphore=True) -> list[Any]:
	if len(coros) == 0:
		return []
	
	def create_task(coro):
		return asyncio.create_task(sem_coro(coro) if use_semaphore else coro)
	
	done, pending = await asyncio.wait([create_task(i) for i in coros], return_when=asyncio.FIRST_EXCEPTION)
	for i in pending:
		i.cancel()
	
	for i in done:
		if isinstance(i.exception(), Exception): #ignore BaseException
			raise i.exception()
	return [i.result() for i in done]