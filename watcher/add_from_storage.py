import asyncio
import json
import traceback

from accounts.client import AccountsClient, SingleAccountsClient
from accounts.types import ListTaskInfo
from helper.db_config import db
from helper.db_config import start as db_start

from .actions import IAction, load_action_by_info, modes
from .last_task_state import LastTaskState
from .unpaid_rewards import UnpaidRewards


def get_account_id(s: str) -> str | None:
    start = 'near-api-js:keystore:'
    ending = ':mainnet'

    if s.startswith(start) and s.endswith(ending):
        return s[len(start):-len(ending)]
    return None

async def safe_load_action(account: SingleAccountsClient, task: ListTaskInfo) -> IAction:
    try:
        return await load_action_by_info(account, task)
    except Exception:  # noqa: BLE001
        print(account.account_id, task, traceback.format_exc())

async def add_account(account_id: str, private_key: str) -> None:
    async with db.transaction():
        async with AccountsClient([]) as c:
            await c.add_key(account_id, private_key)

        async with SingleAccountsClient(account_id) as c:
            if not c.connected:
                print(f'cannot connect to {account_id}')
                return

            mode_tasks = await asyncio.gather(*[c.get_task_list(mode) for mode in modes])
            state = await LastTaskState.get(account_id)
            ended_tasks = {i.task_id for i in state if i.ended}

            actions = []
            for tasks in mode_tasks:
                if tasks is None:
                    print('WTF:', account_id)
                    continue

                for i in tasks:
                    if i.task_id in ended_tasks:
                        continue

                    actions.append(safe_load_action(c, i))

            actions: list[IAction] = await asyncio.gather(*actions)


            await LastTaskState.bulk_update([
                LastTaskState(account_id=account_id, task_id=i.task_id, ended=i.has_ended(), resubmits=i.info.resubmits) for i in actions
            ])
            await UnpaidRewards.clear(account_id)
    print('OK:', account_id)

async def main() -> None:
    await db_start()
    data = []

    with open('sessionStorage.json') as file:  # noqa: ASYNC101
        j = json.load(file)

    for k, v in j.items():
        account_id = get_account_id(k)
        if account_id is None:
            continue
        data.append((account_id, v))
    await asyncio.gather(*[add_account(*i) for i in data])

asyncio.run(main())
