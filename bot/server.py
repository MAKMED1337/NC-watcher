from .client import PORT

from helper.IPC import Server, Connection, Packet, Response, FuncCall
from helper.report_exceptions import report_exception
from helper.bot_config import bot
from helper.db_config import db

from watcher.actions import IAction, get_payment_cost, modes, qualities
from watcher.unpaid_rewards import UnpaidRewards, ActionEnum
from .connected_accounts import ConnectedAccounts
import html

server = Server(PORT, Connection, report_exception)

async def notify_payment(action: IAction, reward: UnpaidRewards):
	print(action.info)
	print(reward)
	assert isinstance(action, IAction), type(action)
	#assert isinstance(reward, UnpaidRewards), type(reward)       <- 'sqlalchemy.engine.row.Row'

	info = action.info
	text = f'TX: <code>{reward.tx_id}</code>\n\n'
	text += f'Account: <code>{reward.account_id}</code>\n'
	text += f'Action: {reward.action.name.capitalize()}\n'
	text += f'{modes[info.mode].name}({info.task_id}): <pre>{html.escape(info.short_descr)}</pre>\n\n'

	if reward.action == ActionEnum.review:
		text += 'Your verdict: <b>' + ('Rejected' if info.my_verdict == 0 else qualities[info.my_quality]) + '</b>'
		text += ', final verdict: <b>' + ('Rejected' if info.status == 3 else qualities[info.quality]) + '</b>\n'
		text += f'Your comment: <pre>{html.escape(action.get_my_review()["comment"])}</pre>\n\n'
	else:
		text += 'Verdict: <b>' + ('Rejected' if info.status == 3 else qualities[info.quality]) + '</b>\n'
		if len(info.reviews) > 0:
			text += f'Comment: <pre>{html.escape(info.reviews[-1]["comment"])}</pre>\n\n'
		else:
			text += f'Your comment(resubmitted): <pre>{html.escape(info.comment)}</pre>\n\n'
		text += f'Resubmits: <b>{info.resubmits}</b>\n\n'

	text += f'Price: <b>{get_payment_cost(reward) / 1000}</b>Ⓝ'
	await bot.send_message('@makmed1337', text[:4096])

async def remove_key(account_id: str, private_key: str):
	await bot.send_message('@makmed1337', f'Account was deleted: <code>{account_id}</code>')

@server.on_connect
async def on_client_connect(conn: Connection):
	while conn.is_active():
		packet: Packet = await conn.read(None)
		if packet is None:
			break

		call: FuncCall = packet.data
		assert call.name in ('notify_payment', 'remove_key')

		resp = Response(conn, packet)
		await resp.respond(await call.apply(globals()[call.name]))