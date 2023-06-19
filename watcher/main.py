from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter
from .config import bot, review_watcher_interval

import asyncio
from helper.provider_config import provider
from .unpaid_rewards import UnpaidRewards, ActionEnum
from helper.db_config import start as db_start
from accounts.client import AccountsClient
from helper.async_helper import *
from .block_processor import process_new_blocks, set_coef, last_block_logger
from .actions import *
from bot.connected_accounts import ConnectedAccounts
from .resolve_and_pay import resolve_and_pay

block_logger = None
wrong_review_watcher = None

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

async def main():
	await start()
	while True:
		await fetch_coef()
		await process_new_blocks()
		
		actions = await UnpaidRewards.get_unpaid_action_types()
		tasks = [asyncio.sleep(1)]
		for account_id, action in actions:
			tasks.append(resolve_and_pay(account_id, action))
		await wait_pool(tasks)

async def stop():
	await provider.close()
	await stop_reporter()
	if block_logger is not None:
		block_logger.cancel()
	if wrong_review_watcher is not None:
		wrong_review_watcher.cancel()

if __name__ == '__main__':
	main_handler(main, report_exception, stop)