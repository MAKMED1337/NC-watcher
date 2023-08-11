import asyncio
import base64
import json
import sys
from typing import Any

from accounts.client import AccountsClient
from bot.connected_accounts import ConnectedAccounts
from helper.async_helper import wait_pool
from helper.db_config import db
from helper.provider_config import provider
from helper.report_exceptions import report

from .block_retriever import auto_retry, retrieve_new_blocks
from .config import block_logger_interval
from .processed_blocks import ProcessedBlocks
from .unpaid_rewards import ActionEnum, UnpaidRewards

coef = None

def set_coef(c: float) -> None:
    global coef
    coef = c

async def add_reward_if_connected(tx_id: str, account_id: str, cost: float, action: ActionEnum, adjustment: int | None = None) -> None:
    if await ConnectedAccounts.is_connected(account_id):
        await UnpaidRewards.add(tx_id, account_id, cost, coef, action, adjustment)

async def process_reward(tx_id: str, args: dict) -> None:
    await add_reward_if_connected(tx_id, args['performed_by'], args['mnear_per_task'] * args['verdict'], ActionEnum.task, args['verdict'])

    for reviewer, adjustment in zip(args['reviewers'], args['adjustments'], strict=True):
        if adjustment == 5:  # noqa: PLR2004
            continue
        assert 0 <= adjustment <= 2  # noqa: PLR2004
        await add_reward_if_connected(tx_id, reviewer, args['mnear_per_review'], ActionEnum.review, adjustment)

async def verify_keys(account_id: str) -> None:
    if await ConnectedAccounts.is_connected(account_id):
        async with AccountsClient([]) as c:
            await c.verify_keys(account_id)

async def process_chunk(chunk: dict[str, Any]) -> None:
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

async def process_new_blocks() -> None:
    async def process_block(block: dict[str, Any]) -> None:
        block_id = block['header']['height']

        #chunk processing
        #not using semaphore cause already called with semaphore and cause loop(like mutex)
        chunks = await wait_pool([auto_retry(provider.get_chunk, chunk['chunk_hash']) for chunk in block['chunks']], use_semaphore=False)

        async with db.transaction():
            for chunk in chunks:
                await process_chunk(chunk)
            await ProcessedBlocks.set_processed(block_id)

    await retrieve_new_blocks(process_block)

async def last_block_logger() -> None:
    prev = None
    while True:
        block_id = await ProcessedBlocks.get_last_id()
        print('block_id:', block_id)
        if block_id == prev:
            await report(f'blocks stuck on {block_id}')
            sys.exit(1)

        prev = block_id
        await asyncio.sleep(block_logger_interval.seconds)
