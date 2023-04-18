from near.providers import JsonProvider 
from pathlib import Path
from bot.client import BotClient

directory = Path(__file__).parent.resolve()

provider = JsonProvider('https://rpc.mainnet.near.org')

bot = BotClient()