import asyncio

from reporter.client import ReporterClient


async def main() -> None:
    r = ReporterClient()
    await r.connect()
    for i in range(1, 4):
        await r.report(str(i))
    await r.close()

if __name__ == '__main__':
    asyncio.run(main())
