import os

from telethon import TelegramClient

BOT_NAME = os.getenv('BOT_NAME')

#Uses only command name. For example `command_to_regex('hello')`
def command_to_regex(command: str) -> str:
    return fr'\/{command}(@{BOT_NAME})?$'

bot = TelegramClient(os.getenv('BOT_NAME'), os.getenv('API_ID'), os.getenv('API_HASH'), catch_up=True)
bot.parse_mode = 'html'

async def start() -> None:
    await bot.start(bot_token=os.getenv('TOKEN'))
    await bot.catch_up()

async def run() -> None:
    await start()
    await bot.run_until_disconnected()
