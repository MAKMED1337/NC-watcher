from reporter.client import ReporterClient
import asyncio

async def main():
	r = ReporterClient()
	await r.connect()
	for i in range(1, 4):
		await r.report(str(i))
	await r.close()

if __name__ == '__main__':
	asyncio.run(main())