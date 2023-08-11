import asyncio
import os
import traceback
from pathlib import Path

import sd_notify
from telethon import events
from telethon.types import Message

from helper.bot_config import bot
from helper.bot_config import start as start_bot
from helper.IPC import Connection, Server
from helper.main_handler import main_handler

from .client import PORT

GROUP_ID = int(os.getenv('GROUP_ID'))
reports = Path(__file__).parent / 'reports'


log_index = 1
def invalidate_index() -> None:
    global log_index
    log_index = 1


# returns path to file
def create_file() -> None:
    global log_index

    reports.mkdir(parents=True, exist_ok=True)
    while True:
        path = reports / (str(log_index) + '.txt')
        if not path.is_file():
            return path
        log_index += 1


async def report(message: str) -> None:
    print(message)

    file = create_file()
    print(file)

    with open(file, 'w', encoding='utf-8') as f:  # noqa: ASYNC101
        f.write(message)

    text = f'<code>{file.name}</code>\n\n<code>{{}}</code>'
    max_message_len = 4096 - len(text) + 2

    message = message.replace('<', '&lt').replace('>', '&gt')
    text = text.replace('{}', message[:max_message_len])

    await bot.send_message(GROUP_ID, text)


@bot.on(events.NewMessage(pattern='/close$'))
async def close(event: Message) -> None:
    if not event.is_reply:
        return await event.reply('Use as reply')

    issue = await event.get_reply_message()
    if issue.sender != await bot.get_me():
        return await event.reply("Use reply on bot's message")

    try:
        filename = issue.get_entities_text()[0][1]
    except Exception:  # noqa: BLE001
        return await event.reply("Can't obtain filename")

    (reports / filename).unlink()
    invalidate_index()
    await issue.delete()
    await event.delete()
    return None


async def exception_handler(exc: Exception) -> None:
    await report(''.join(traceback.format_exception(exc)))

server = Server(PORT, Connection, exception_handler)


@server.on_connect
async def on_client_connect(conn: Connection) -> None:
    while conn.is_active():
        msg = await conn.read(None)
        if msg is None:
            break
        await report(msg)


async def start_all() -> None:
    await start_bot()
    await server.start()
    sd_notify.Notifier().ready()

    tasks = [asyncio.create_task(i) for i in [bot.run_until_disconnected(), server.run()]]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for i in done:
        exc = i.exception()
        if exc is not None:
            raise exc


async def stop_all() -> None:
    await server.close()

if __name__ == '__main__':
    main_handler(start_all, report, stop_all)
