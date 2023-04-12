from .client import PORT

from helper.IPC import Server, Connection
from helper.main_handler import main_handler
from helper.report_exceptions import report_exception
from helper.bot_config import bot, run as run_bot

import asyncio
from watcher.actions import IAction, get_payment_cost, modes, qualities
from watcher.unpaid_rewards import UnpaidRewards, ActionEnum
from dataclasses import asdict
import html

server = Server(PORT, Connection, report_exception)

@server.on_connect
async def on_client_connect(conn: Connection):
	while conn.is_active():
		msg = await conn.read(None)
		if msg is None:
			break
		
		action, reward = msg
		print(action, reward)
		assert isinstance(action, IAction), type(action)
		#assert isinstance(reward, UnpaidRewards), type(reward)       <- 'sqlalchemy.engine.row.Row'
		action: IAction
		reward: UnpaidRewards

		#text = f'raw:\n\n<code>{reward.tx_id}</code>\ncost: <code>{get_payment_cost(reward)}</code>\n\n<pre>{reward._mapping}</pre>\n\n<pre>{asdict(action.info)}</pre>'
		#await bot.send_message('@makmed1337', text[:4096])

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
			text += f'Comment: <pre>{html.escape(info.reviews[-1]["comment"])}</pre>\n\n'
			text += f'Resubmits: <b>{info.resubmits}</b>\n\n'

		text += f'Price: <b>{get_payment_cost(reward) / 1000}</b>Ⓝ'
		await bot.send_message('@makmed1337', text[:4096])

async def start_all():
	tasks = [asyncio.create_task(i) for i in [run_bot(), server.run()]]
	done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
	for i in done:
		exc = i.exception()
		if exc is not None:
			raise exc

async def stop_all():
	await server.close()

if __name__ == '__main__':
	main_handler(start_all, report_exception, stop_all)