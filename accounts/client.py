PORT = 2001



from helper.IPC import FuncClient
from .nearcrowd_account import V2
import json
from pydantic import BaseModel
from dataclasses import dataclass
from typing import Any

def json_or_none(s: str | None):
	if s is None:
		return None
	return json.loads(s)

class QueryParams(BaseModel):
	on_exception: Any = Exception
	retries: int | None = None

@dataclass
class ListTaskInfo:
	mode: int
	task_id: int
	my_quality: int
	my_verdict: int
	quality: int
	short_descr: str
	status: int

	def __init__(self, data: dict):
		self.mode = data['mode']
		self.task_id = data['user_task_id']
		self.my_quality = data['my_quality']
		self.my_verdict = data['my_verdict']
		self.quality = data['quality']
		self.short_descr = data['short_descr']
		self.status = data['status']

def identity(x):
	return x

class AccountsClient(FuncClient):
	def __init__(self, account_ids: list[str] | None = None):
		super().__init__(PORT)
		self.account_ids = account_ids
		self.queries = []
	
	async def connect(self) -> list[str]:
		await super().connect()
		return await self.set_accounts(self.account_ids)

	async def __aenter__(self):
		await self.connect()
		return self

	#accountless
	async def set_accounts(self, account_ids: list[str] | None, on_exception: Any=Exception) -> list[str]:
		self.account_ids = account_ids
		ids = await self.call(on_exception, 'set_accounts', account_ids)
		self.connected_ids = ids
		return ids

	#create or update key
	async def create_account(self, account_id: str, private_key: str, on_exception: Any=Exception) -> bool:
		return await self.call(on_exception, 'create_account', account_id, private_key)

	async def delete_account(self, account_id: str, on_exception: Any=Exception):
		return await self.call(on_exception, 'delete_account', account_id)
	
	async def is_connected(self, account_id: str, on_exception: Any=Exception) -> bool:
		return await self.call(on_exception, 'is_connected', account_id)

	async def get_coef(self, on_exception: Any=Exception) -> float:
		return await self.call(on_exception, 'get_coef')

	async def get_access_keys(self, account_id: str, on_exception: Any=Exception):
		return await self.call(on_exception, 'get_access_keys', account_id)



	async def _query(self, q: V2, params=QueryParams(), callback=identity) -> dict[str, str]:
		if params.retries is not None:
			q.retry_count = params.retries
		return {k: callback(v) for k, v in (await self.call(params.on_exception, 'query', q)).items()}

	async def _query_json(self, q: V2, params=QueryParams()) -> dict[str, dict]:
		return await self._query(q, params, json_or_none)



	async def claim_task(self, mode: int, Q: str = '', params=QueryParams()) -> dict[str, str]:
		return await self._query(V2(path=f'v2/claim_task/{mode}', Q=Q), params)

	async def claim_review(self, mode: int, Q: str = '', params=QueryParams()) -> dict[str, str]:
		return await self._query(V2(path=f'v2/claim_review/{mode}', Q=Q), params)

	async def get_status(self, mode: int, params=QueryParams()) -> dict[str, dict]:
		return await self._query_json(V2(path=f'v2/taskset/{mode}'), params)

	async def get_task(self, mode: int, task_id: int, params=QueryParams()) -> dict[str, dict]:
		return await self._query_json(V2(path=f'v2/get_task/{mode}/{task_id}', args={'user_task_id': task_id}), params)

	async def get_pillar(self, pillar_id: int, params=QueryParams()) -> dict[str, dict]:
		return await self._query_json(V2(path=f'pillars/pillar/{pillar_id}', name='pillars'), params)

	async def get_task_list(self, mode: int, params=QueryParams()) -> list[ListTaskInfo]:
		def callback(r):
			r = json_or_none(r)
			if r is None:
				return None
			
			for i in range(len(r)):
				r[i]['mode'] = mode
			return [ListTaskInfo(i) for i in r]
		return await self._query(V2(path=f'v2/get_old_tasks/{mode}', name='v2'), params, callback)


class SingleAccountsClient(AccountsClient):
	def __init__(self, account_id: str):
		super().__init__(PORT)
		self.account_ids = [account_id]
		self.account_id = account_id

	async def connect(self) -> bool:
		await super().connect()
		self.connected = self.connected_ids == self.account_ids
		return self.connected

	async def set_accounts(self, *args, **kwargs):
		await super().set_accounts(*args, **kwargs)

	async def create_account(self, *args, **kwargs):
		raise NotImplementedError

	async def delete_account(self, *args, **kwargs):
		raise NotImplementedError
	
	async def _query(self, *args, **kwargs) -> str:
		r = await super()._query(*args, **kwargs)
		return r[self.account_id]