from .client import PORT

from helper.IPC import Server, Connection
from helper.main_handler import main_handler
from helper.bot_config import bot, run as run_bot, start as start_bot

import asyncio
from pathlib import Path
import traceback
from telethon import events
import os

GROUP_ID = 1830719850
reports = Path(__file__).parent / 'reports'

log_index = 1
def invalidate_index():
	global log_index
	log_index = 1

# returns path to file
def create_file():
	global log_index
	
	reports.mkdir(parents=True, exist_ok=True)
	while True:
		path = reports / (str(log_index) + '.txt')
		if not path.is_file():
			return path
		log_index += 1

async def report(message: str):
	print(message)

	file = create_file()
	print(file)
	open(file, 'w', encoding='utf-8').write(message)

	text = f'<code>{file.name}</code>\n\n<code>{{}}</code>'
	max_message_len = 4096 - len(text) + 2

	message = message.replace('<', '&lt').replace('>', '&gt')
	text = text.replace('{}', message[:max_message_len])
	
	await bot.send_message(GROUP_ID, text)

@bot.on(events.NewMessage(pattern='/close$'))
async def close(event):
	if not event.is_reply:
		return await event.reply('Use as reply')
	
	issue = await event.get_reply_message()
	if issue.sender != await bot.get_me():
		return await event.reply('Use reply on bot\'s message')

	try:
		filename = issue.get_entities_text()[0][1]
	except Exception:
		return await event.reply('Can\'t obtain filename')
	
	os.remove(reports / filename)
	invalidate_index()
	await issue.delete()
	await event.delete()

@bot.on(events.NewMessage(pattern='/close_all$'))
async def close_all(event):
	#TODO implement
	return

async def exception_handler(exc: Exception):
	await report(''.join(traceback.format_exception(exc)))

server = Server(PORT, Connection, exception_handler)

@server.on_connect
async def on_client_connect(conn: Connection):
	while conn.is_active():
		msg = await conn.read(None)
		if msg is None:
			break
		await report(msg)

async def start_all():
	await start_bot()
	tasks = [asyncio.create_task(i) for i in [bot.run_until_disconnected(), server.run()]]
	done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
	for i in done:
		exc = i.exception()
		if exc is not None:
			raise exc

async def stop_all():
	await server.close()

if __name__ == '__main__':
	main_handler(start_all, report, stop_all)