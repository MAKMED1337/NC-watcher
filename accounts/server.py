from .client import PORT

from helper.IPC import Server, FuncCall, Connection, Response, Packet
from helper.main_handler import main_handler
from helper.report_exceptions import report_exception

from .nearcrowd_account import NearCrowdAccount
from helper.provider_config import provider
from .accounts_db import Accounts
import helper.db_config as db_config
from .locks import get_lock
from .functions import *
import asyncio
from typing import Any
import sd_notify

server = Server(PORT, Connection, report_exception)
TIMEOUT = 30


async def get_account(account_id: str) -> NearCrowdAccount | None:
	try:
		private_key = await Accounts.get_key(account_id)
		return NearCrowdAccount(account_id, private_key)
	except Exception:
		return None

async def apply_accountless(call: FuncCall):
	return await call.apply(globals()[call.name])

async def apply_for_accounts(accounts: NearCrowdAccount | list[NearCrowdAccount], call: FuncCall):
	return await asyncio.gather(*[call.apply(globals()[call.name], i) for i in accounts])

async def get_accounts_list() -> list[NearCrowdAccount]:
	return [NearCrowdAccount(account_id, private_key) for account_id, private_key in await Accounts.get_accounts_credentials()]

async def lock_account(account: NearCrowdAccount):
	await get_lock(account.account_id).acquire()
	return account

async def lock_accounts(accounts: list[NearCrowdAccount]) -> list[NearCrowdAccount]:
	if len(accounts) == 0:
		return []
	
	tasks = [asyncio.create_task(lock_account(i)) for i in accounts]
	done, pending = await asyncio.wait(tasks, timeout=TIMEOUT)
	for i in pending:
		i.cancel()
	return [i.result() for i in done]

def unlock(accounts: list[NearCrowdAccount]):
	for i in accounts:
		get_lock(i.account_id).release()

async def get_locked_accounts(account_ids: list[str] | None) -> list[NearCrowdAccount]:
	assert isinstance(account_ids, list | None), type(account_ids)

	if account_ids is None:
		accounts = await get_accounts_list()
	else:
		accounts = await asyncio.gather(*[get_account(i) for i in account_ids])
	
	accounts = list(filter(lambda x: x is not None, accounts))
	return await lock_accounts(accounts)

def get_ids(accounts: list[NearCrowdAccount]) -> list[str]:
	return [i.account_id for i in accounts]

class ConnectionHandler:
	def __init__(self, conn: Connection) -> None:
		self.conn = conn
		self.accounts = []

	async def proceed_client(self):	
		tasks = []
		while self.conn.is_active():
			try:
				packet: Packet = await self.conn.read(timeout=TIMEOUT)
				assert isinstance(packet, Packet), type(packet)
				tasks.append(asyncio.create_task(self._proceed_call(Response(self.conn, packet))))
			except TimeoutError:
				if all([task.done() for task in tasks]):
					print('Probably forgot to close connection', self.accounts)
					break
				else:
					continue
			except Exception:
				break
		
		unlock(self.accounts)
		for task in tasks:
			task.cancel()
		await self.conn.close()

	async def _proceed_call(self, resp: Response):
		await resp.respond(await self.execute_call(resp.data))

	async def execute_call(self, call: FuncCall) -> Any:
		assert isinstance(call, FuncCall), type(call)

		if call.name in ('set_accounts'):
			unlock(self.accounts)
			self.accounts = await call.apply(get_locked_accounts)
			return get_ids(self.accounts)

		if call.name in ('create_account', 'is_connected', 'get_coef', 'get_access_keys', 'verify_keys'):
			return await apply_accountless(call)
		
		assert call.name in ('query'), call.name
		result = await apply_for_accounts(self.accounts, call)
		return {k.account_id: v for k, v in zip(self.accounts, result)}

@server.on_connect
async def on_client_connect(conn: Connection):
	c = ConnectionHandler(conn)
	await c.proceed_client()

async def start():
	provider.start()
	await db_config.start()
	await server.start()
	sd_notify.Notifier().ready()

	await server.run()

async def stop():
	await provider.close()
	await server.stop()

if __name__ == '__main__':
	main_handler(start, report_exception, server.close)