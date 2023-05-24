from .nearcrowd_account import NearCrowdAccount, V2
from .accounts_db import Accounts
from bot.client import BotClient
from near.signer import KeyPair

async def query(account: NearCrowdAccount, q: V2) -> str:
	return await account.query(q)

async def create_account(account_id: str, private_key: str) -> bool:
	try:
		account = NearCrowdAccount(account_id, private_key)
		if not await account.check_account():
			return False
		
		await Accounts.add_account(account_id, private_key)
		return True
	except Exception:
		return False

async def is_connected(account_id: str) -> bool:
	return await Accounts.is_connected(account_id)

async def get_coef() -> float:
	return await NearCrowdAccount.get_coef()

async def get_access_keys(account_id: str):
	return await NearCrowdAccount.get_access_keys(account_id)

#returns removed keys
async def update_keys(account_id: str) -> list[str]:
	public_keys = await get_access_keys(account_id)
	keys = await Accounts.get_keys(account_id)

	broken_keys = [key for key in keys if KeyPair(key).public_key not in public_keys]
	
	for key in broken_keys:
		await _delete_key(account_id, key)
	return broken_keys

async def _delete_key(account_id: str, private_key: str):
	await Accounts.delete_key(account_id, private_key)
	try:
		async with BotClient() as bot:
			await bot.remove_key(account_id, private_key)
	except Exception:
		pass