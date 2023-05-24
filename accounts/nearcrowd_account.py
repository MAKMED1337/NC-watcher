import base64
import json
import asyncio
import aiohttp
from pydantic import BaseModel
from enum import Enum
from typing import Any

from near.signer import Signer, KeyPair
from near import transactions
from near.account import Account
from near.providers import JsonProvider, FinalityTypes

class PostType(Enum):
	data = 'body'
	json = 'json'

class PostData(BaseModel):
	type: PostType
	data: Any

class V2(BaseModel):
	path: str
	Q: str = ''
	args: dict = {}
	name: str = 'v2'
	post: PostData | None = None

	retry_count: int = 10

contract_id = 'app.nearcrowd.near'
api = 'https://nearcrowd.com/'

class InvalidKeyException(Exception):
	pass

class NearCrowdAccount:
	def __init__(self, account_id: str, private_key: str):
		self._signer = Signer(account_id, KeyPair(private_key))

	@property
	def account_id(self):
		return self._signer.account_id

	def get_nearcrowd_tx(self, actions: list[transactions.Action]):
		nonce = 0
		block_hash = b'\0' * 32
		return transactions.sign_and_serialize_transaction(contract_id, nonce, actions, block_hash, self._signer)

	def get_tx_args(self, args: dict = {}, name: str='v2'):
		args = str.encode(json.dumps(args))
		encoded_tx = self.get_nearcrowd_tx([transactions.create_function_call_action(name, args, 0, 0)])
		return base64.b64encode(encoded_tx).decode('ascii')
	
	def get_tx(self, name: str='v2'):
		return self.get_tx_args(name=name)

	async def check_account(self):
		async with JsonProvider('https://rpc.mainnet.near.org') as provider:
			account = Account(provider, self._signer)
			await account.start()
			return await account.view_function(contract_id, 'is_account_whitelisted', {'account_id': self._signer.account_id})

	#return public keys
	@staticmethod
	async def get_access_keys(account_id: str) -> list[str]:
		result = []
		async with JsonProvider('https://rpc.mainnet.near.org') as provider:
			for key in (await provider.get_access_key_list(account_id, FinalityTypes.FINAL))['keys']:
				access_key = key['access_key']
				permission = access_key['permission']
				if permission == 'FullAccess' or permission['FunctionCall']['receiver_id'] == contract_id:
					result.append(key['public_key'])
		return result


	# MAYBE add status ?
	async def _query_one_try(self, q: V2) -> str:
		encodedTx = self.get_tx_args(q.args, q.name)
		url = f'{api}{q.path}/{encodedTx}{q.Q}'
		post = q.post

		async with aiohttp.ClientSession() as session:
			if post is None:
				request = session.get(url)
			else:
				request = session.post(url, **{post.type: post.data}, headers={'Content-Type': 'application/json'})

			async with request as response:
				text = await response.text()
				if not response.ok and text.endswith('AssertionError: Access key not found\n'):
					raise InvalidKeyException()
				response.raise_for_status()

				return text

	async def query(self, q: V2) -> str:
		for _ in range(q.retry_count):
			try:
				return await self._query_one_try(q)
			except Exception:
				await asyncio.sleep(1)



	@staticmethod
	async def fetch_accountless(path: str, retries: int=10):
		for _ in range(retries):
			try:
				async with aiohttp.ClientSession() as session:
					async with session.get(f'{api}{path}') as response:
						response.raise_for_status()
						return await response.text()
			except Exception:
				await asyncio.sleep(1)
	
	@staticmethod
	async def get_coef(retries: int=10):
		return await NearCrowdAccount.fetch_accountless('get_coef', retries)