from near.providers import JsonProvider 
import asyncio
from pathlib import Path

directory = Path(__file__).parent.resolve()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

provider = JsonProvider('https://rpc.mainnet.near.org')