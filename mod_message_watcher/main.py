import asyncio

from accounts.client import AccountsClient, QueryParams
from helper.db_config import start as db_start
from helper.main_handler import main_handler
from helper.report_exceptions import report_exception, stop_reporter

from .acknowledged_messages import AcknowledgedMessages
from .config import bot, timeout


async def main() -> None:
    await db_start()
    await bot.connect()

    while True:
        async with AccountsClient() as c:
            mod_messages = await c.get_mod_message(QueryParams(on_exception={}))

        for account_id, message in mod_messages.items():
            if message is None:
                continue

            msg_id = message.id
            if await AcknowledgedMessages.is_acknowledged(msg_id):
                continue

            try:
                await bot.notify_mod_message(account_id, message.msg)
                await AcknowledgedMessages.acknowledge(msg_id)
            except Exception as exc:  # noqa: BLE001
                await report_exception(exc)

        await asyncio.sleep(timeout.seconds)


async def stop() -> None:
    await stop_reporter()


if __name__ == '__main__':
    main_handler(main, report_exception, stop)
