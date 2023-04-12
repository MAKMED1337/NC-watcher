from near.providers import JsonProvider 
import asyncio
from pathlib import Path

directory = Path(__file__).parent.resolve()

provider = JsonProvider('https://rpc.mainnet.near.org')