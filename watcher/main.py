import asyncio

from accounts.client import AccountsClient
from bot.connected_accounts import ConnectedAccounts
from helper.async_helper import wait_pool
from helper.db_config import start as db_start
from helper.main_handler import main_handler
from helper.provider_config import provider
from helper.report_exceptions import report_exception, stop_reporter

from .block_processor import last_block_logger, process_new_blocks, set_coef
from .config import bot, review_watcher_interval
from .resolve_and_pay import resolve_and_pay
from .unpaid_rewards import ActionEnum, UnpaidRewards

block_logger = None
wrong_review_watcher = None


async def fetch_coef() -> None:
    for _i in range(100):
        async with AccountsClient([]) as c:
            coef = await c.get_coef(None)
            if coef is not None:
                set_coef(coef)
                return
        await asyncio.sleep(1)
    raise Exception('Too many tries to fetch coef')  # noqa: TRY002


async def review_watcher() -> None:
    while True:
        tasks = []
        for account_id in await ConnectedAccounts.get_watched_accounts():
            tasks.append(resolve_and_pay(account_id, ActionEnum.review))
        await wait_pool(tasks)
        await asyncio.sleep(review_watcher_interval.seconds)


async def start() -> None:
    global block_logger, wrong_review_watcher
    provider.start()
    await db_start()
    await bot.connect()

    #process new blocks for first time without limits
    await fetch_coef()
    await process_new_blocks()

    block_logger = asyncio.create_task(last_block_logger())
    wrong_review_watcher = asyncio.create_task(review_watcher())


async def main() -> None:
    await start()
    while True:
        await fetch_coef()
        await process_new_blocks()

        actions = await UnpaidRewards.get_unpaid_action_types()
        tasks = [asyncio.sleep(1)]
        for account_id, action in actions:
            tasks.append(resolve_and_pay(account_id, action))
        await wait_pool(tasks)


async def stop() -> None:
    await provider.close()
    await stop_reporter()
    if block_logger is not None:
        block_logger.cancel()
    if wrong_review_watcher is not None:
        wrong_review_watcher.cancel()


if __name__ == '__main__':
    main_handler(main, report_exception, stop)
