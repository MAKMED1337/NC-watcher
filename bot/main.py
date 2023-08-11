import asyncio

import sd_notify

from helper.bot_config import bot
from helper.bot_config import start as start_bot
from helper.db_config import start as start_db
from helper.main_handler import main_handler
from helper.report_exceptions import report_exception

from .interaction import bot_interaction  # noqa: F401 only loads to catch events
from .server import server


async def start_all() -> None:
    await start_db()
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
    main_handler(start_all, report_exception, stop_all)
