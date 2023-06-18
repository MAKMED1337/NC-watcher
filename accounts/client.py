PORT = 2001



from helper.IPC import FuncClient
from .nearcrowd_account import V2
import json
from pydantic import BaseModel
from typing import Any, Callable, TypeVar
from .types import *

T = TypeVar('T')

def json_or_none(s: str | None):
	if s is None:
		return None
	return json.loads(s)

class QueryParams(BaseModel):
	on_exception: Any = Exception
	retries: int | None = None

def identity(x: T) -> T:
	return x

def typify(cls: T):
	def f(j: str) -> T | None:
		j: dict = json_or_none(j)
		return cls(j) if j is not None else None
	return f

#TODO: add normal types, insted of dict[str, ...]
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

	#create or add key
	async def add_key(self, account_id: str, private_key: str, on_exception: Any=Exception) -> bool:
		return await self.call(on_exception, 'create_account', account_id, private_key)
	
	async def is_connected(self, account_id: str, on_exception: Any=Exception) -> bool:
		return await self.call(on_exception, 'is_connected', account_id)

	async def get_coef(self, on_exception: Any=Exception) -> float:
		return await self.call(on_exception, 'get_coef')

	async def get_access_keys(self, account_id: str, on_exception: Any=Exception) -> list[str]:
		return await self.call(on_exception, 'get_access_keys', account_id)

	async def verify_keys(self, account_id: str, on_exception: Any=Exception) -> list[str]:
		return await self.call(on_exception, 'verify_keys', account_id)



	async def _query(self, q: V2, params=QueryParams(), callback: Callable[[str], T]=identity) -> dict[str, T]:
		if params.retries is not None:
			q.retry_count = params.retries
		return {k: callback(v) for k, v in (await self.call(params.on_exception, 'query', q)).items()}

	async def _query_json(self, q: V2, params=QueryParams()) -> dict[str, dict]:
		return await self._query(q, params, json_or_none)



	async def claim_task(self, mode: int, Q: str = '', params=QueryParams()):
		return await self._query(V2(path=f'v2/claim_task/{mode}', Q=Q), params)

	async def claim_review(self, mode: int, Q: str = '', params=QueryParams()):
		return await self._query(V2(path=f'v2/claim_review/{mode}', Q=Q), params)

	async def get_status(self, mode: int, params=QueryParams()):
		return await self._query(V2(path=f'v2/taskset/{mode}'), params, typify(Status))

	async def get_task(self, mode: int, task_id: int, params=QueryParams()):
		return await self._query(V2(path=f'v2/get_task/{mode}/{task_id}', args={'user_task_id': task_id}), params, typify(InnerTaskInfo))

	async def get_pillar(self, pillar_id: int, params=QueryParams()):
		return await self._query_json(V2(path=f'pillars/pillar/{pillar_id}', name='pillars'), params)

	async def get_task_list(self, mode: int, params=QueryParams()):
		def callback(r) -> list[ListTaskInfo] | None:
			r = json_or_none(r)
			if r is None:
				return None
			
			for i in range(len(r)):
				r[i]['mode'] = mode
			return [ListTaskInfo(i) for i in r]
		return await self._query(V2(path=f'v2/get_old_tasks/{mode}', name='v2'), params, callback)

	async def get_mod_message(self, params=QueryParams()):
		def callback(r) -> ModMessage | None:
			r = json_or_none(r)
			if r is None or len(r) == 0:
				return None
			return ModMessage(r)
		return await self._query(V2(path=f'mod_message', name='mod'), params, callback)


class SingleAccountsClient(AccountsClient):
	def __init__(self, account_id: str):
		super().__init__(PORT)
		self.account_ids = [account_id]
		self.account_id = account_id

	@property
	def connected(self) -> bool:
		return super().connected and self.connected_ids == self.account_ids

	async def connect(self) -> bool:
		await super().connect()
		return self.connected

	async def add_key(self, *args, **kwargs):
		raise NotImplementedError

	async def get_access_keys(self, on_exception: Any=Exception) -> list[str]:
		return await self.call(on_exception, 'get_access_keys', self.account_id)

	async def verify_keys(self, on_exception: Any=Exception) -> list[str]:
		return await self.call(on_exception, 'verify_keys', self.account_id)
	

	
	async def _query(self, q: V2, params=QueryParams(), callback: Callable[[str], T]=identity) -> T:
		r = await super()._query(q, params, callback)
		return r[self.account_id]
	
	async def claim_task(self, mode: int, Q: str = '', params=QueryParams()) -> str:
		return await super().claim_task(mode, Q, params)

	async def claim_review(self, mode: int, Q: str = '', params=QueryParams()) -> str:
		return await super().claim_review(mode, Q, params)

	async def get_status(self, mode: int, params=QueryParams()) -> Status:
		return await super().get_status(mode, params)

	async def get_task(self, mode: int, task_id: int, params=QueryParams()) -> InnerTaskInfo:
		return await super().get_task(mode, task_id, params)

	async def get_pillar(self, pillar_id: int, params=QueryParams()) -> dict:
		return await super().get_pillar(pillar_id, params)

	async def get_task_list(self, mode: int, params=QueryParams()) -> list[ListTaskInfo]:
		return await super().get_task_list(mode, params)

	async def get_mod_message(self, params=QueryParams()) -> ModMessage | None:
		return await super().get_mod_message(params)