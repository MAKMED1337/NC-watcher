PORT = 2001



import json  # noqa: E402
from collections.abc import Callable  # noqa: E402
from typing import Any, Self, TypeVar  # noqa: E402

from pydantic import BaseModel  # noqa: E402

from helper.IPC import FuncClient  # noqa: E402

from .nearcrowd_account import V2  # noqa: E402
from .types import InnerTaskInfo, ListTaskInfo, ModMessage, Pillar, Status  # noqa: E402

T = TypeVar('T')


def json_or_none(s: str | None) -> dict | None:
    if s is None:
        return None
    return json.loads(s)


class QueryParams(BaseModel):
    on_exception: Any = Exception
    retries: int | None = None


def identity(x: T) -> T:
    return x


def typify(cls: type[T]) -> Callable[[str], T | None]:
    def f(j: str) -> T | None:
        j: dict = json_or_none(j)
        return cls(j) if j is not None else None
    return f


Accounts = dict[str, T]
#TODO: add normal types, insted of dict[str, ...]
class AccountsClient(FuncClient):
    def __init__(self, account_ids: list[str] | None = None) -> None:
        super().__init__(PORT)
        self.account_ids = account_ids

    async def connect(self) -> list[str]:
        await super().connect()
        return await self.set_accounts(self.account_ids)

    async def __aenter__(self) -> Self:
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


    async def _query(self, q: V2, params: QueryParams = QueryParams(), callback: Callable[[str], T]=identity) -> Accounts[T]:
        if params.retries is not None:
            q.retry_count = params.retries
        return {k: callback(v) for k, v in (await self.call(params.on_exception, 'query', q)).items()}

    async def _query_json(self, q: V2, params: QueryParams = QueryParams()) -> dict[str, dict]:
        return await self._query(q, params, json_or_none)


    async def claim_task(self, mode: int, Q: str = '', params: QueryParams = QueryParams()) -> Accounts[str | int | None]:
        def parse_status(s: str | None) -> str | int | None:
            try:
                return int(s)
            except ValueError:
                return s
        return await self._query(V2(path=f'v2/claim_task/{mode}', Q=Q), params, parse_status)

    async def claim_review(self, mode: int, Q: str = '', params: QueryParams = QueryParams()) -> Accounts[str | None]:
        return await self._query(V2(path=f'v2/claim_review/{mode}', Q=Q), params)

    async def postpone(self, mode: int, params: QueryParams = QueryParams()) -> Accounts[str | None]:
        return await self._query(V2(path=f'v2/postpone_task/{mode}'), params)

    async def get_status(self, mode: int, params: QueryParams = QueryParams()) -> Accounts[Status | None]:
        return await self._query(V2(path=f'v2/taskset/{mode}'), params, typify(Status))

    async def get_task(self, mode: int, task_id: int, params: QueryParams = QueryParams()) -> Accounts[InnerTaskInfo | None]:
        return await self._query(V2(path=f'v2/get_task/{mode}/{task_id}', args={'user_task_id': task_id}), params, typify(InnerTaskInfo))

    async def get_pillar(self, pillar_id: int, params: QueryParams = QueryParams()) -> Accounts[Pillar | None]:
        return await self._query(V2(path=f'pillars/pillar/{pillar_id}', name='pillars'), params, typify(Pillar))

    async def get_task_list(self, mode: int, params: QueryParams = QueryParams()) -> Accounts[list[ListTaskInfo] | None]:
        def callback(r: str) -> list[ListTaskInfo] | None:
            r = json_or_none(r)
            if r is None:
                return None

            for i in range(len(r)):
                r[i]['mode'] = mode
            return [ListTaskInfo(i) for i in r]
        return await self._query(V2(path=f'v2/get_old_tasks/{mode}', name='v2'), params, callback)

    async def get_mod_message(self, params: QueryParams = QueryParams()) -> Accounts[ModMessage | None]:
        def callback(r: str | None) -> ModMessage | None:
            r = json_or_none(r)
            if r is None or len(r) == 0:
                return None
            return ModMessage(r)
        return await self._query(V2(path='mod_message', name='mod'), params, callback)


class SingleAccountsClient:
    def __init__(self, account_id: str) -> None:
        self.__client = AccountsClient([account_id])
        self.account_id = account_id

        original_query = self.__client._query  # noqa: SLF001
        async def query(*args: Any, **kwargs: Any) -> Any:
            r = await original_query(*args, **kwargs)
            return r[self.account_id]
        self.__client._query = query  # noqa: SLF001, maybe create more abstract class, that accepts query as function

    async def __aenter__(self) -> Self:
        await self.__client.__aenter__()
        return self

    async def __aexit__(self, *args: list[Any]) -> None:
        await self.__client.__aexit__(*args)

    @property
    def connected(self) -> bool:
        return self.__client.connected and self.__client.connected_ids == [self.account_id]

    async def connect(self) -> bool:
        await self.__client.connect()
        return self.connected

    async def get_access_keys(self, on_exception: Any=Exception) -> list[str]:
        return await self.__client.get_access_keys(on_exception)

    async def verify_keys(self, on_exception: Any=Exception) -> list[str]:
        return await self.__client.verify_keys(on_exception)


    async def claim_task(self, mode: int, Q: str = '', params: QueryParams = QueryParams()) -> str | int | None:
        return await self.__client.claim_task(mode, Q, params)

    async def claim_review(self, mode: int, Q: str = '', params: QueryParams = QueryParams()) -> str | None:
        return await self.__client.claim_review(mode, Q, params)

    async def postpone(self, mode: int, params: QueryParams = QueryParams()) -> str | None:
        return await self.__client.postpone(mode, params)

    async def get_status(self, mode: int, params: QueryParams = QueryParams()) -> Status | None:
        return await self.__client.get_status(mode, params)

    async def get_task(self, mode: int, task_id: int, params: QueryParams = QueryParams()) -> InnerTaskInfo | None:
        return await self.__client.get_task(mode, task_id, params)

    async def get_pillar(self, pillar_id: int, params: QueryParams = QueryParams()) -> Pillar | None:
        return await self.__client.get_pillar(pillar_id, params)

    async def get_task_list(self, mode: int, params: QueryParams = QueryParams()) -> list[ListTaskInfo] | None:
        return await self.__client.get_task_list(mode, params)

    async def get_mod_message(self, params: QueryParams = QueryParams()) -> ModMessage | None:
        return await self.__client.get_mod_message(params)
