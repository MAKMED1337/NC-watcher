from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter, report
from .config import bot, timeout
from accounts.client import AccountsClient
from .acknowledged_messages import AcknowledgedMessages

from typing import Any
from helper.db_config import db, start as db_start
import asyncio

async def main():
	await db_start()
	await bot.connect()

	while True:
		async with AccountsClient() as c:
			mod_messages = await c.get_mod_message({})
		
		for account_id, message in mod_messages.items():
			if 'id' not in message:
				continue
			
			msg_id = message['id']
			if await AcknowledgedMessages.is_acknowledged(msg_id):
				continue
			
			try:
				await bot.notify_mod_message(account_id, message['msg'])
				await AcknowledgedMessages.acknowledge(msg_id)
			except Exception as exc:
				await report_exception(exc)
		
		await asyncio.sleep(timeout.seconds)

async def stop():
	await stop_reporter()

if __name__ == '__main__':
	main_handler(main, report_exception, stop)