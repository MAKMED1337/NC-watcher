import asyncio
import html
import json
from enum import Enum

from telethon import events
from telethon.types import Message

from accounts.client import AccountsClient, SingleAccountsClient
from helper.bot_config import bot, command_to_regex
from helper.db_config import db
from helper.report_exceptions import report_exception
from watcher.actions import IAction, load_action_by_info, modes
from watcher.last_task_state import LastTaskState
from watcher.unpaid_rewards import UnpaidRewards

from ..connected_accounts import ConnectedAccounts  # noqa: TID252


def get_account_id(s: str) -> str | None:
    start = 'near-api-js:keystore:'
    ending = ':mainnet'

    if s.startswith(start) and s.endswith(ending):
        return s[len(start):-len(ending)]
    return None

#only adds account, doesn't connect
async def add_account_unsafe(account_id: str, private_key: str) -> bool:
    async with db.transaction():
        async with AccountsClient([]) as c:
            if not await c.add_key(account_id, private_key):
                return False

        already_connected = await ConnectedAccounts.is_connected(account_id)
        print(account_id, '->', 'connected' if already_connected else 'new')
        if already_connected:
            return True

        #adding data into db
        async with SingleAccountsClient(account_id) as c:
            assert c.connected

            mode_tasks = await asyncio.gather(*[c.get_task_list(mode) for mode in modes])
            state = await LastTaskState.get(account_id)
            ended_tasks = {i.task_id for i in state if i.ended}

            actions = []
            for tasks in mode_tasks:
                if tasks is None:
                    continue

                for i in tasks:
                    if i.task_id in ended_tasks:
                        continue

                    actions.append(load_action_by_info(c, i))

            actions: list[IAction] = await asyncio.gather(*actions)

            await LastTaskState.bulk_update([
                LastTaskState(account_id=account_id, task_id=i.task_id, ended=i.has_ended(), resubmits=i.info.resubmits) for i in actions
            ])
            await UnpaidRewards.clear(account_id)
    return True

class AdditionStatus(Enum):
    ok = 0
    bad = 1
    bug = 2

async def add_account(account_id: str, private_key: str) -> AdditionStatus:
    try:
        return AdditionStatus.ok if await add_account_unsafe(account_id, private_key) else AdditionStatus.bad
    except Exception as e:  # noqa: BLE001
        await report_exception(e)
        return AdditionStatus.bug


@bot.on(events.NewMessage(pattern=command_to_regex('list')))
async def get_accounts_list(message: Message) -> None:
    accounts = await ConnectedAccounts.get_connected_accounts(message.sender_id)
    text = ''
    for account_id in accounts:
        text += f'<code>{account_id}</code>\n'
    await message.reply(text)
    raise events.StopPropagation


def listify_accounts(accounts: list[str]) -> None:
    text = ''
    for account_id in accounts:
        text += f'<code>{account_id}</code>\n'
    return text


@bot.on(events.NewMessage(incoming=True))
async def add_accounts_handler(message: Message) -> None:
    try:
        accounts = json.loads(html.unescape(message.text))
    except json.JSONDecodeError:
        await message.reply('Invalid JSON')
        return

    data = []
    for k, v in accounts.items():
        account_id = get_account_id(k)
        if account_id is None:
            continue
        data.append((account_id, v))
    statuses = await asyncio.gather(*[add_account(*i) for i in data])

    ok, bad, bug = [], [], []
    for (account_id, private_key), status in zip(data, statuses, strict=True):
        if status == AdditionStatus.ok:
            await ConnectedAccounts.add(message.sender_id, account_id, private_key)
            ok.append(account_id)
        elif status == AdditionStatus.bad:
            bad.append(account_id)
        else:
            bug.append(account_id)

    text = 'Succesfully connected:\n' + listify_accounts(ok)

    if len(bad) > 0:
        text += "\nWasn't connected:\n" + listify_accounts(bad)

    if len(bug) > 0:
        text += '\nBugged(report to admins):\n' + listify_accounts(bug)

    await message.reply(text[:4096])
