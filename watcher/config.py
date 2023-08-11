from datetime import timedelta
from pathlib import Path

from bot.client import BotClient

directory = Path(__file__).parent.resolve()
block_logger_interval = timedelta(minutes=10)
review_watcher_interval = timedelta(minutes=5)

bot = BotClient()
