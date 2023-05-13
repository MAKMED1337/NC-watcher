from .client import AccountsClient
import asyncio
import json

def get_account_id(s: str) -> str | None:
	start = 'near-api-js:keystore:'
	ending = ':mainnet'

	if s.startswith(start) and s.endswith(ending):
		return s[len(start):-len(ending)]

async def main():
	c = AccountsClient()
	await c.connect()

	data = []
	for k, v in json.load(open('sessionStorage.json', 'r')).items():
		account_id = get_account_id(k)
		if account_id is None:
			continue
		data.append((account_id, v))
	
	result = await asyncio.gather(*[c.create_account(k, v) for k, v in data])
	print('\n'.join([f'{account_id} -> {r}' for (account_id, key), r in zip(data, result)]))

	await c.close()

if __name__ == '__main__':
	asyncio.run(main())