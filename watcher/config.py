from pathlib import Path
from bot.client import BotClient
from datetime import timedelta

directory = Path(__file__).parent.resolve()
block_logger_interval = timedelta(minutes=10)

bot = BotClient()