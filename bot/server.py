import contextlib
import html

from accounts.client import AccountsClient
from helper.bot_config import bot
from helper.IPC import Connection, FuncCall, Packet, Response, Server
from helper.report_exceptions import report_exception
from watcher.actions import IAction, Status, get_payment_cost, modes, qualities
from watcher.unpaid_rewards import ActionEnum, UnpaidRewards

from .config import PORT
from .connected_accounts import ConnectedAccounts

server = Server(PORT, Connection, report_exception)

async def send_to_connected(account_id: str, text: str) -> None:
    async with AccountsClient([]) as c:
        await c.verify_keys(account_id)

    for tg_id in await ConnectedAccounts.get_tg(account_id):
        with contextlib.suppress(Exception):
            await bot.send_message(tg_id, text[:4096])


async def notify_payment(action: IAction, reward: UnpaidRewards) -> None:
    print(action.info.debug)
    print(reward)
    assert isinstance(action, IAction), type(action)

    account_id = reward.account_id

    info = action.info
    text = f'TX: <code>{reward.tx_id}</code>\n\n'
    text += f'Account: <code>{account_id}</code>\n'
    text += f'Action: {reward.action.name.capitalize()}\n'
    text += f'{modes[info.mode].name}({info.task_id}): <pre>{html.escape(info.short_descr)}</pre>\n\n'

    if reward.action == ActionEnum.review:
        text += 'Your verdict: <b>' + ('Rejected' if info.my_verdict == 0 else qualities[info.my_quality]) + '</b>'
        text += ', final verdict: <b>' + ('Rejected' if info.status == Status.reject else qualities[info.quality]) + '</b>\n'
        text += f'Your comment: <pre>{html.escape(action.get_my_review().comment)}</pre>\n\n'
    else:
        text += 'Verdict: <b>' + ('Rejected' if info.status == Status.reject else qualities[info.quality]) + '</b>\n'
        if len(info.reviews) > 0:
            text += f'Comment: <pre>{html.escape(info.reviews[-1].comment)}</pre>\n\n'
        else:
            text += f'Your comment(resubmitted): <pre>{html.escape(info.comment)}</pre>\n\n'
        text += f'Resubmits: <b>{info.resubmits}</b>\n\n'

    text += f'Price: <b>{get_payment_cost(reward) / 1000}</b>Ⓝ'
    await send_to_connected(account_id, text)


async def remove_key(account_id: str, private_key: str) -> None:
    for tg_id in await ConnectedAccounts.get_tg_by_key(account_id, private_key):
        with contextlib.suppress(Exception):
            await bot.send_message(tg_id, f'Account was disconnected: <code>{account_id}</code>')

    await ConnectedAccounts.remove_key(account_id, private_key)


async def notify_mod_message(account_id: str, msg: str) -> None:
    text = f'Account: <code>{account_id}</code>\n\n'
    text += f'Moderators have sent you the following message:\n\n<pre>{html.escape(msg)}</pre>'
    await send_to_connected(account_id, text[:4096])


@server.on_connect
async def on_client_connect(conn: Connection) -> None:
    while conn.is_active():
        packet: Packet = await conn.read(None)
        if packet is None:
            break

        call: FuncCall = packet.data
        assert call.name in ('notify_payment', 'remove_key', 'notify_mod_message')

        resp = Response(conn, packet)
        await resp.respond(await call.apply(globals()[call.name]))
