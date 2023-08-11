import asyncio
import json

from .client import AccountsClient


def get_account_id(s: str) -> str | None:
    start = 'near-api-js:keystore:'
    ending = ':mainnet'

    if s.startswith(start) and s.endswith(ending):
        return s[len(start):-len(ending)]
    return None

async def main() -> None:
    c = AccountsClient([])
    await c.connect()

    data = []
    with open('sessionStorage.json') as f:  # noqa: ASYNC101
        j = json.load(f)

    for k, v in j.items():
        account_id = get_account_id(k)
        if account_id is None:
            continue
        data.append((account_id, v))

    result = await asyncio.gather(*[c.add_key(k, v) for k, v in data])
    print('\n'.join([f'{account_id} -> {r}' for (account_id, key), r in zip(data, result, strict=True)]))

    await c.close()

if __name__ == '__main__':
    asyncio.run(main())
